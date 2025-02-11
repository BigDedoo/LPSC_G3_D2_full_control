# utils/state_machine_builder.py

from PyQt5.QtCore import QState, QFinalState, QStateMachine

def build_acq_state_machine(worker):
    """
    Builds and returns a QStateMachine configured for the acquisition sequence.
    The passed 'worker' object is expected to define:
      - Signals: initDone, motorYDone, startSequenceDone, profileReady, aCommandSent,
                 pollSuccess, pollTimeout, dCommandSent, dataCollected, dataSaved.
      - Methods: on_state_init, on_state_sendMotorY, on_state_startSequence,
                 on_state_processProfile, on_state_sendACommand, on_state_pollForResponse,
                 on_state_sendDCommand, on_state_collectData, on_state_saveData.
    """
    machine = QStateMachine()

    state_init = QState()
    state_sendMotorY = QState()
    state_startSequence = QState()
    state_processProfile = QState()
    state_sendACommand = QState()
    state_pollForResponse = QState()
    state_sendDCommand = QState()
    state_collectData = QState()
    state_saveData = QState()
    state_final = QFinalState()

    # Set up transitions using worker signals.
    state_init.addTransition(worker.initDone, state_sendMotorY)
    state_sendMotorY.addTransition(worker.motorYDone, state_startSequence)
    state_startSequence.addTransition(worker.startSequenceDone, state_processProfile)
    state_processProfile.addTransition(worker.profileReady, state_sendACommand)
    state_sendACommand.addTransition(worker.aCommandSent, state_pollForResponse)
    state_pollForResponse.addTransition(worker.pollSuccess, state_sendDCommand)
    state_pollForResponse.addTransition(worker.pollTimeout, state_final)
    state_sendDCommand.addTransition(worker.dCommandSent, state_collectData)
    state_collectData.addTransition(worker.dataCollected, state_saveData)
    state_saveData.addTransition(worker.dataSaved, state_processProfile)

    # Connect on-entry functions.
    state_init.entered.connect(worker.on_state_init)
    state_sendMotorY.entered.connect(worker.on_state_sendMotorY)
    state_startSequence.entered.connect(worker.on_state_startSequence)
    state_processProfile.entered.connect(worker.on_state_processProfile)
    state_sendACommand.entered.connect(worker.on_state_sendACommand)
    state_pollForResponse.entered.connect(worker.on_state_pollForResponse)
    state_sendDCommand.entered.connect(worker.on_state_sendDCommand)
    state_collectData.entered.connect(worker.on_state_collectData)
    state_saveData.entered.connect(worker.on_state_saveData)

    for state in [state_init, state_sendMotorY, state_startSequence,
                  state_processProfile, state_sendACommand, state_pollForResponse,
                  state_sendDCommand, state_collectData, state_saveData, state_final]:
        machine.addState(state)
    machine.setInitialState(state_init)
    return machine
