classDiagram
    %% Application Layer
    namespace Application {
        class SimulationCoordinator {
            -MachineRegistry machineRegistry
            -PlayerRegistry playerRegistry
            -EventDispatcher eventDispatcher
            -SessionFactory sessionFactory
            -TaskExecutor taskExecutor
            +runSimulation(config)
            -generatePairs(config)
            -calculatePreferences()
        }
        class SessionRunner {
            -GamingSession session
            -EventDispatcher eventDispatcher
            +run()
        }
        class MachineRegistry {
            -MachineFactory machineFactory
            -ConfigLoader configLoader
            -Map~String, SlotMachine~ machines
            +loadMachines(configDir)
            +getMachine(machineId)
        }
        class PlayerRegistry {
            -PlayerFactory playerFactory
            -ConfigLoader configLoader
            -Map~String, Player~ players
            +loadPlayers(configDir)
            +getPlayer(playerId)
        }
        class RegistryService {
            -MachineRegistry machineRegistry
            -PlayerRegistry playerRegistry
            +loadFromConfig(config)
            +resetAll()
        }
    }

    %% Domain Layer 
    namespace Domain {
        class SlotMachine {
            -String id
            -List~Reel~ reels
            -WinEvaluationService winService
            +spin(betAmount)
        }
        class Player {
            -String id
            -float balance
            -DecisionEngine decisionEngine
            +play(machineId, sessionData)
            +shouldEndSession(machineId, sessionData)
        }
        class GamingSession {
            -String id
            -Player player
            -SlotMachine machine
            -List~SpinResult~ results
            +start()
            +executeSpin(betAmount)
            +end()
            +getStatistics()
        }
        class EventDispatcher {
            -Map handlers
            +register(eventType, handler)
            +dispatch(event)
        }
    }

    %% Relationships
    SimulationCoordinator --> MachineRegistry : uses
    SimulationCoordinator --> PlayerRegistry : uses
    SimulationCoordinator --> SessionRunner : creates
    SimulationCoordinator --> EventDispatcher : uses
    SessionRunner --> GamingSession : runs
    MachineRegistry --> SlotMachine : manages
    PlayerRegistry --> Player : manages
    GamingSession --> Player : references
    GamingSession --> SlotMachine : references
    RegistryService --> MachineRegistry : owns
    RegistryService --> PlayerRegistry : owns