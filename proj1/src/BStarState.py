import time

STATE_PRIMARY = 1
STATE_BACKUP = 2
STATE_ACTIVE = 3
STATE_PASSIVE = 4

PEER_PRIMARY = 1
PEER_BACKUP = 2
PEER_ACTIVE = 3
PEER_PASSIVE = 4
CLIENT_REQUEST = 5


class BStarState(object):
    def __init__(self, state, event, peer_expiry):
        self.state = state
        self.event = event
        self.peer_expiry = peer_expiry


class BStarException(Exception):
    pass


fsm_states = {
    STATE_PRIMARY: {
        PEER_BACKUP: ("I: connected to backup , ready as PRIMARY (ACTIVE)",
                      STATE_ACTIVE),
        PEER_ACTIVE: ("I: connected to backup (ACTIVE), ready as primary",
                      STATE_PASSIVE)
    },
    STATE_BACKUP: {
        PEER_ACTIVE: ("I: connected to primary(ACTIVE) , ready as BACKUP",
                      STATE_PASSIVE),
        CLIENT_REQUEST: ("", False)
    },
    STATE_ACTIVE: {
        PEER_ACTIVE: (
            "E: fatal error - both servers are ACTIVE, aborting", False)
    },
    STATE_PASSIVE: {
        PEER_PRIMARY: ("I: primary (slave) is restarting, ready as master",
                       STATE_ACTIVE),
        PEER_BACKUP: ("I: backup (slave) is restarting, ready as master",
                      STATE_ACTIVE),
        PEER_PASSIVE: ("E: fatal error - BOTH SERVERS INACTIVE, aborting", False),
        CLIENT_REQUEST: (CLIENT_REQUEST, True)  # Say true, check peer later
    }
}


def run_fsm(fsm):
    # There are some transitional states we do not want to handle
    state_dict = fsm_states.get(fsm.state, {})
    res = state_dict.get(fsm.event)
    if res:
        msg, state = res
    else:
        return
    if state is False:
        raise BStarException(msg)
    elif msg == CLIENT_REQUEST:
        assert fsm.peer_expiry > 0
        if int(time.time() * 1000) > fsm.peer_expiry:
            fsm.state = STATE_ACTIVE
        else:
            raise BStarException()
    else:
        print(msg)
        fsm.state = state
