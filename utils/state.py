_gym_wizard = {}

def set_gym_wizard(user_id, mode, step, data=None):
    _gym_wizard[str(user_id)] = {'mode': mode, 'step': step, 'data': data or {}}

def get_gym_wizard(user_id):
    return _gym_wizard.get(str(user_id))

def clear_gym_wizard(user_id):
    _gym_wizard.pop(str(user_id), None)