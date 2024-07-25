import asyncio
from typing import Any

from pykit.res import Ok, Res
from pykit.uuid import uuid4

from rxcat import ConnArgs, ServerBus, ServerBusCfg, ServerRegData, Transport
from tests.conftest import Mock_1, Mock_2, MockConn


async def test_main():
    async def reg_fn(
            tokens: list[str],
            client_data: dict[str, Any] | None) -> Res[ServerRegData]:
        assert tokens == ["whocares_1", "whocares_2"]
        assert client_data == {"name": "mark"}
        return Ok(ServerRegData(data={"state": 12}))

    flag = False
    async def sub__f(data: Mock_1):
        nonlocal flag
        flag = True

    sbus = ServerBus.ie()
    cfg = ServerBusCfg(
        transports=[
            Transport(
                is_server=True,
                conn_type=MockConn,
                is_registration_enabled=True)
        ],
        reg_types=[
            Mock_1,
            Mock_2
        ],
        reg_fn=reg_fn)
    await asyncio.wait_for(sbus.init(cfg), 1)

    conn = MockConn(ConnArgs(core=None))
    conn_task = asyncio.create_task(sbus.conn(conn))

    await conn.client__send({
        "sid": uuid4(),
        "datacodeid": 0,
        "data": {
            "tokens": ["whocares_1", "whocares_2"],
            "data": {
                "name": "mark"
            }
        }
    })
    server_reg_evt = await asyncio.wait_for(conn.client__recv(), 1)
    assert server_reg_evt["datacodeid"] == 1
    assert server_reg_evt["data"]["data"] == {"state": 12}
    welcome = await asyncio.wait_for(conn.client__recv(), 1)
    assert welcome["datacodeid"] == 2

    (await sbus.sub(Mock_1, sub__f)).eject()
    (await sbus.pub(Mock_1(num=1))).eject()

    assert flag

    conn_task.cancel()