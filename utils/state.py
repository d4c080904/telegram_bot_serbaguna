from database.queries import save_wizard_state, get_wizard_state, delete_wizard_state

# ONBOARDING WIZARD
async def set_onboarding_wizard(user_id, step, data):
    await save_wizard_state(user_id, "onboarding", step, data)

async def get_onboarding_wizard(user_id):
    return await get_wizard_state(user_id, "onboarding")

async def clear_onboarding_wizard(user_id):
    await delete_wizard_state(user_id, "onboarding")

# GYM WIZARD
async def set_gym_wizard(user_id, mode, step):
    await save_wizard_state(user_id, "gym", step, {"mode": mode})

async def get_gym_wizard(user_id):
    return await get_wizard_state(user_id, "gym")

async def clear_gym_wizard(user_id):
    await delete_wizard_state(user_id, "gym")