from database.queries import save_wizard_state, get_wizard_state, delete_wizard_state

# --- GYM WIZARD ---
def set_gym_wizard(user_id, mode, step, data=None):
    state_data = {'mode': mode, 'data': data or {}}
    save_wizard_state(user_id, 'gym', step, state_data)

def get_gym_wizard(user_id):
    state = get_wizard_state(user_id, 'gym')
    if state:
        return {'mode': state['data'].get('mode'), 'step': state['step'], 'data': state['data'].get('data', {})}
    return None

def clear_gym_wizard(user_id):
    delete_wizard_state(user_id, 'gym')

# --- ONBOARDING WIZARD ---
def set_onboarding_wizard(user_id, step, data=None):
    save_wizard_state(user_id, 'onboarding', step, data or {})

def get_onboarding_wizard(user_id):
    state = get_wizard_state(user_id, 'onboarding')
    if state:
        return {'step': state['step'], 'data': state['data']}
    return None

def clear_onboarding_wizard(user_id):
    delete_wizard_state(user_id, 'onboarding')