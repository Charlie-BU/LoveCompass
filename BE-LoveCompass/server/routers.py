from robyn import SubRouter

# Define the sub-router
router = SubRouter(__file__, prefix="")


@router.get("/")
async def index():
    return "OK"


# Expose a function to register this router (optional, or just import 'router' directly)
def register_routers(app):
    app.include_router(router)
