# Example: OptionForge Mapping

This is an optional example. Read it only when you need to map the generic skill concepts onto this repository.

## Repository mapping

- Orchestration layer
  - `src/strategy/application/`
  - Examples: event bridge, market workflow, lifecycle workflow, subscription workflow, state workflow.
- Domain services
  - `src/strategy/domain/domain_service/`
  - Examples: selection, signal, pricing, risk, execution, hedging, combination.
- Domain objects
  - `src/strategy/domain/entity/`, `src/strategy/domain/value_object/`, `src/strategy/domain/event/`
- Infrastructure adapters
  - `src/strategy/infrastructure/gateway/`
  - `src/strategy/infrastructure/persistence/`
  - `src/strategy/infrastructure/monitoring/`

## Concrete examples

- Contract filtering maps well to `option_selector_service.py`.
- Signal decisions map well to `signal_service.py` and the signal value objects.
- Pricing and greek workflows map well to the pricing service modules.
- Restart state currently uses persistence snapshots plus historical replay inputs.
- Monitoring projections already live in a separate monitoring subsystem, which is a good example of keeping monitoring apart from restart state.

## Project-specific cautions

- Do not let new strategy logic bypass the current separation between application workflows, domain services, and infrastructure adapters.
- Do not move monitoring persistence into the restart persistence module.
- When extending broker integration, keep vn.py-specific transport details inside gateway adapters instead of leaking them into domain services.
