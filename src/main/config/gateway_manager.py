"""
gateway_manager.py - 网关连接编排

职责:
1. 加载并注册网关
2. 基于 vn.py CTP TD/MD 状态位判断 readiness
3. 提供事件驱动的等待能力
4. 在运行中断线时执行有限次重连
"""
from __future__ import annotations

import copy
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from vnpy.event import Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import (
    EVENT_ACCOUNT,
    EVENT_CONTRACT,
    EVENT_LOG,
    EVENT_POSITION,
)

from src.main.bootstrap.ctp_tick_patch import patch_ctp_pre_settlement_price


class GatewayStatus(Enum):
    """网关状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class GatewayState:
    """网关状态快照。"""

    name: str
    status: GatewayStatus = GatewayStatus.DISCONNECTED
    connected_time: Optional[float] = None
    contract_count: int = 0
    td_connected: bool = False
    td_login: bool = False
    auth_status: bool = False
    md_connected: bool = False
    md_login: bool = False
    contract_inited: bool = False
    last_stage: str = ""
    last_error: str = ""
    last_update_ts: Optional[float] = None
    reconnect_attempts: int = 0


class GatewayManager:
    """
    统一管理交易网关的配置、连接、状态和重连。
    """

    GATEWAY_CLASS_MAP: Dict[str, type] = {
        "ctp": None,
    }

    _WATCHED_EVENTS = (
        EVENT_LOG,
        EVENT_CONTRACT,
        EVENT_ACCOUNT,
        EVENT_POSITION,
    )
    _RECONNECT_DELAYS = (1.0, 3.0, 10.0)

    def __init__(self, main_engine: MainEngine) -> None:
        self.main_engine = main_engine
        self.logger = logging.getLogger(__name__)

        self.configs: Dict[str, Dict[str, Any]] = {}
        self.states: Dict[str, GatewayState] = {}

        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._event_engine = getattr(main_engine, "event_engine", None)
        self._event_handlers_registered = False
        self._active_profile = "trading"
        self._shutdown = False
        self._reconnect_timers: Dict[str, threading.Timer] = {}

        self._load_gateway_classes()

    def _load_gateway_classes(self) -> None:
        """动态加载网关类。"""
        patch_ctp_pre_settlement_price(self.logger)
        from vnpy_ctp import CtpGateway

        self.GATEWAY_CLASS_MAP["ctp"] = CtpGateway

    def set_config(self, config: Dict[str, Any]) -> None:
        """设置网关配置。"""
        with self._condition:
            self.configs = config
            self.states = {
                gateway_name: GatewayState(name=gateway_name)
                for gateway_name in self.configs.keys()
            }
            self._shutdown = False

        self.logger.info("已设置网关配置: %s", list(self.configs.keys()))

    def add_gateways(self) -> None:
        """添加所有配置的网关到主引擎。"""
        for gateway_name in self.configs.keys():
            gateway_class = self.GATEWAY_CLASS_MAP.get(gateway_name)

            if gateway_class is None:
                self.logger.warning("不支持的网关类型: %s", gateway_name)
                continue

            self.main_engine.add_gateway(gateway_class)
            self.logger.info("已添加网关: %s", gateway_name)

    def connect_all(self) -> None:
        """连接所有网关。"""
        self._ensure_event_handlers_registered()
        for gateway_name, config in self.configs.items():
            self.connect_gateway(gateway_name, config)

    def connect_gateway(
        self,
        gateway_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """连接指定网关。"""
        setting = config or self.configs.get(gateway_name, {})
        if not setting:
            raise ValueError(f"网关 {gateway_name} 配置为空")

        with self._condition:
            state = self.states.setdefault(gateway_name, GatewayState(name=gateway_name))
            state.status = GatewayStatus.CONNECTING
            state.last_error = ""
            state.last_stage = f"{gateway_name} td=disconnected md=disconnected contracts=idle"
            state.last_update_ts = time.time()
            self._cancel_reconnect_timer_locked(gateway_name)

        try:
            self.main_engine.connect(setting, self._to_vnpy_gateway_name(gateway_name))
            self.logger.info("网关 %s 连接请求已发送", gateway_name)
        except Exception as exc:
            with self._condition:
                state = self.states.setdefault(gateway_name, GatewayState(name=gateway_name))
                state.status = GatewayStatus.ERROR
                state.last_error = str(exc)
                state.last_update_ts = time.time()
            raise

    def disconnect_all(self) -> None:
        """断开所有网关连接并取消内部监听。"""
        with self._condition:
            self._shutdown = True
            for gateway_name in list(self._reconnect_timers):
                self._cancel_reconnect_timer_locked(gateway_name)

        self._unregister_event_handlers()

        if self.main_engine:
            self.main_engine.close()

        with self._condition:
            now = time.time()
            for state in self.states.values():
                state.status = GatewayStatus.DISCONNECTED
                state.connected_time = None
                state.td_connected = False
                state.td_login = False
                state.auth_status = False
                state.md_connected = False
                state.md_login = False
                state.contract_inited = False
                state.last_stage = (
                    f"{state.name} td=disconnected md=disconnected contracts=idle"
                )
                state.last_update_ts = now
            self._condition.notify_all()

    def wait_for_ready(
        self,
        profile: str,
        timeout: float,
        check_interval: float = 0.5,
    ) -> Dict[str, GatewayState]:
        """
        等待所有网关满足指定 readiness profile。

        超时会抛出包含阶段快照的 TimeoutError。
        """
        if profile not in {"trading", "recording"}:
            raise ValueError(f"不支持的 readiness profile: {profile}")

        self._active_profile = profile
        self._ensure_event_handlers_registered()

        deadline = time.monotonic() + timeout
        with self._condition:
            self._refresh_states_locked(profile)

            while not self._all_gateways_ready_locked(profile):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    snapshot = self._describe_states_locked()
                    message = (
                        f"网关 readiness 超时(profile={profile}, timeout={timeout}s): {snapshot}"
                    )
                    self.logger.error(message)
                    raise TimeoutError(message)

                self._condition.wait(timeout=min(check_interval, remaining))
                self._refresh_states_locked(profile)

            return copy.deepcopy(self.states)

    def get_status(self) -> Dict[str, GatewayState]:
        """获取所有网关状态。"""
        with self._condition:
            self._refresh_states_locked(self._active_profile)
            return copy.deepcopy(self.states)

    def is_all_connected(self) -> bool:
        """检查是否所有网关都已满足当前 readiness 条件。"""
        with self._condition:
            self._refresh_states_locked(self._active_profile)
            return self._all_gateways_ready_locked(self._active_profile)

    def get_connected_gateways(self) -> List[str]:
        """获取已满足 readiness 条件的网关名称。"""
        with self._condition:
            self._refresh_states_locked(self._active_profile)
            return [
                name
                for name, state in self.states.items()
                if state.status == GatewayStatus.CONNECTED
            ]

    def _ensure_event_handlers_registered(self) -> None:
        if not self._event_engine or self._event_handlers_registered:
            return

        for event_type in self._WATCHED_EVENTS:
            self._event_engine.register(event_type, self._handle_gateway_event)
        self._event_handlers_registered = True

    def _unregister_event_handlers(self) -> None:
        if not self._event_engine or not self._event_handlers_registered:
            return

        for event_type in self._WATCHED_EVENTS:
            try:
                self._event_engine.unregister(event_type, self._handle_gateway_event)
            except Exception:
                pass
        self._event_handlers_registered = False

    def _handle_gateway_event(self, event: Event) -> None:
        with self._condition:
            self._update_log_error_locked(event)
            self._refresh_states_locked(self._active_profile)
            self._condition.notify_all()

    def _update_log_error_locked(self, event: Event) -> None:
        if getattr(event, "type", "") != EVENT_LOG:
            return

        log = getattr(event, "data", None)
        msg = str(getattr(log, "msg", "") or "")
        if not msg or not any(key in msg for key in ("失败", "错误", "断开", "超时")):
            return

        gateway_name = str(getattr(log, "gateway_name", "") or "").lower()
        targets = [gateway_name] if gateway_name in self.states else list(self.states.keys())
        for name in targets:
            self.states[name].last_error = msg

    def _refresh_states_locked(self, profile: str) -> None:
        now = time.time()
        contract_counts = self._collect_contract_counts()

        for gateway_name, state in self.states.items():
            gateway = self._get_gateway(gateway_name)
            setting = self.configs.get(gateway_name, {})
            previous_status = state.status

            td_api = getattr(gateway, "td_api", None) if gateway else None
            md_api = getattr(gateway, "md_api", None) if gateway else None

            state.td_connected = bool(getattr(td_api, "connect_status", False))
            state.td_login = bool(getattr(td_api, "login_status", False))
            state.auth_status = bool(getattr(td_api, "auth_status", False))
            state.md_connected = bool(getattr(md_api, "connect_status", False))
            state.md_login = bool(getattr(md_api, "login_status", False))
            state.contract_inited = bool(getattr(td_api, "contract_inited", False))
            state.contract_count = contract_counts.get(
                self._to_vnpy_gateway_name(gateway_name), 0
            )
            state.last_stage = self._format_stage(gateway_name, state, setting)
            state.last_update_ts = now

            ready = self._is_ready(profile, state, setting)
            if ready:
                state.status = GatewayStatus.CONNECTED
                if previous_status != GatewayStatus.CONNECTED:
                    state.connected_time = now
                    self.logger.info("网关已就绪: %s", state.last_stage)
                state.reconnect_attempts = 0
                state.last_error = ""
                self._cancel_reconnect_timer_locked(gateway_name)
                continue

            if previous_status == GatewayStatus.CONNECTED:
                state.status = GatewayStatus.CONNECTING
                state.connected_time = None
                if not state.last_error:
                    state.last_error = f"网关状态降级: {state.last_stage}"
                self.logger.warning("检测到网关状态降级: %s", state.last_stage)
                self._schedule_reconnect_locked(gateway_name)
            elif previous_status == GatewayStatus.ERROR and self._has_any_connection(state):
                state.status = GatewayStatus.CONNECTING
            elif previous_status == GatewayStatus.DISCONNECTED and self._has_any_connection(state):
                state.status = GatewayStatus.CONNECTING

    def _collect_contract_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        try:
            contracts = self.main_engine.get_all_contracts()
        except Exception:
            return counts

        for contract in contracts or []:
            gateway_name = str(getattr(contract, "gateway_name", "") or "")
            if not gateway_name:
                continue
            counts[gateway_name] = counts.get(gateway_name, 0) + 1
        return counts

    def _get_gateway(self, gateway_name: str) -> Any:
        vnpy_gateway_name = self._to_vnpy_gateway_name(gateway_name)
        gateway = self.main_engine.get_gateway(vnpy_gateway_name)
        if gateway:
            return gateway
        return self.main_engine.get_gateway(gateway_name)

    @staticmethod
    def _to_vnpy_gateway_name(gateway_name: str) -> str:
        return gateway_name.upper()

    @staticmethod
    def _has_any_connection(state: GatewayState) -> bool:
        return state.td_connected or state.md_connected or state.td_login or state.md_login

    def _is_ready(
        self,
        profile: str,
        state: GatewayState,
        setting: Dict[str, Any],
    ) -> bool:
        requires_auth = self._requires_auth(setting)
        if profile == "recording":
            return state.md_connected and state.md_login and state.contract_inited

        if not (
            state.td_connected
            and state.td_login
            and state.md_connected
            and state.md_login
            and state.contract_inited
        ):
            return False

        if requires_auth and not state.auth_status:
            return False
        return True

    @staticmethod
    def _requires_auth(setting: Dict[str, Any]) -> bool:
        auth_code = str(setting.get("授权编码", "") or "").strip()
        return bool(auth_code)

    def _format_stage(
        self,
        gateway_name: str,
        state: GatewayState,
        setting: Dict[str, Any],
    ) -> str:
        requires_auth = self._requires_auth(setting)

        if not state.td_connected:
            td_stage = "disconnected"
        elif requires_auth and not state.auth_status:
            td_stage = "auth"
        elif state.td_login:
            td_stage = "login"
        else:
            td_stage = "connected"

        if not state.md_connected:
            md_stage = "disconnected"
        elif state.md_login:
            md_stage = "login"
        else:
            md_stage = "connected"

        if state.contract_inited:
            contracts_stage = "ready"
        elif state.td_login or state.md_login:
            contracts_stage = "loading"
        else:
            contracts_stage = "idle"

        return f"{gateway_name} td={td_stage} md={md_stage} contracts={contracts_stage}"

    def _all_gateways_ready_locked(self, profile: str) -> bool:
        if not self.states:
            return False
        return all(
            self._is_ready(profile, state, self.configs.get(name, {}))
            for name, state in self.states.items()
        )

    def _describe_states_locked(self) -> str:
        if not self.states:
            return "no-gateway-configured"
        return "; ".join(
            self.states[name].last_stage or f"{name} td=disconnected md=disconnected contracts=idle"
            for name in self.states
        )

    def _schedule_reconnect_locked(self, gateway_name: str) -> None:
        if self._shutdown:
            return
        if gateway_name in self._reconnect_timers:
            return

        state = self.states[gateway_name]
        if state.reconnect_attempts >= len(self._RECONNECT_DELAYS):
            state.status = GatewayStatus.ERROR
            state.last_error = (
                f"重连次数已达上限({len(self._RECONNECT_DELAYS)}): {state.last_stage}"
            )
            self.logger.error("网关重连失败: %s", state.last_error)
            return

        delay = self._RECONNECT_DELAYS[state.reconnect_attempts]
        state.reconnect_attempts += 1

        timer = threading.Timer(delay, self._execute_reconnect, args=(gateway_name,))
        timer.daemon = True
        self._reconnect_timers[gateway_name] = timer
        timer.start()
        self.logger.warning(
            "将在 %.1fs 后尝试第 %d 次重连: %s",
            delay,
            state.reconnect_attempts,
            gateway_name,
        )

    def _execute_reconnect(self, gateway_name: str) -> None:
        with self._condition:
            self._reconnect_timers.pop(gateway_name, None)
            if self._shutdown:
                return
            setting = self.configs.get(gateway_name, {})

        try:
            self.main_engine.connect(setting, self._to_vnpy_gateway_name(gateway_name))
            self.logger.info("已发起网关重连: %s", gateway_name)
        except Exception as exc:
            with self._condition:
                state = self.states[gateway_name]
                state.status = GatewayStatus.ERROR
                state.last_error = f"重连异常: {exc}"
                state.last_update_ts = time.time()
                self.logger.error("网关重连异常: %s, error=%s", gateway_name, exc)
                self._condition.notify_all()
                return

        with self._condition:
            self._refresh_states_locked(self._active_profile)
            self._condition.notify_all()

    def _cancel_reconnect_timer_locked(self, gateway_name: str) -> None:
        timer = self._reconnect_timers.pop(gateway_name, None)
        if timer:
            timer.cancel()
