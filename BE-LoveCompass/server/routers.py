from robyn import SubRouter
from robyn.robyn import Response

# Define the sub-router
router = SubRouter(__file__, prefix="")


# 异常处理
@router.exception
def handle_exception(error):
    return Response(status_code=500, headers={}, description=f"error msg: {error}")


@router.get("/")
async def index():
    return "OK"


@router.get("/error")
async def error():
    raise Exception("test error")


# Expose a function to register this router (optional, or just import 'router' directly)
def register_routers(app):
    app.include_router(router)
