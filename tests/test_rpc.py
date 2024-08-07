import asyncio
from typing import Any

from pydantic import BaseModel
from ryz.code import get_fqname
from ryz.err import ValErr
from ryz.res import Err, Ok, Res
from ryz.uuid import uuid4

from tests.conftest import (
    EmptyMock,
    MockCon,
    find_codeid_in_welcome_rbmsg,
)
from yon import ConArgs, ServerBus, srpc


async def test_main(sbus: ServerBus):
    class UpdEmailArgs(BaseModel):
        username: str
        email: str
    async def srpc__update_email(msg: UpdEmailArgs) -> Res[int]:
        username = msg.username
        email = msg.email
        if username == "throw":
            return Err(ValErr("hello"))
        assert username == "test_username"
        assert email == "test_email"
        return Ok(0)

    con_1 = MockCon(ConArgs(
        core=None))
    con_task_1 = asyncio.create_task(sbus.con(con_1))

    welcome_rbmsg = await asyncio.wait_for(con_1.client__recv(), 1)
    yon_rpc_req_codeid = find_codeid_in_welcome_rbmsg(
        "yon::srpc_send", welcome_rbmsg).eject()

    ServerBus.reg_rpc(srpc__update_email).eject()

    rpc_key = "update_email"
    await con_1.client__send({
        "sid": uuid4(),
        "codeid": yon_rpc_req_codeid,
        "msg": {
            "key": rpc_key,
            "data": {"username": "test_username", "email": "test_email"}
        }
    })
    rpc_rbmsg = await asyncio.wait_for(con_1.client__recv(), 1)
    rpc_msg = rpc_rbmsg["msg"]
    assert rpc_msg == 0

    rpc_key = "update_email"
    send_msid = uuid4()
    await con_1.client__send({
        "sid": send_msid,
        "codeid": yon_rpc_req_codeid,
        "msg": {
            "key": rpc_key,
            "data": {"username": "throw", "email": "test_email"}
        }
    })
    rpc_rbmsg = await asyncio.wait_for(con_1.client__recv(), 1)
    assert rpc_rbmsg["lsid"] == send_msid
    rpc_msg = rpc_rbmsg["msg"]
    assert rpc_msg["errcode"] == ValErr.code()
    assert rpc_msg["msg"] == "hello"
    assert rpc_msg["name"] == get_fqname(ValErr())

    con_task_1.cancel()

async def test_srpc_decorator():
    @srpc
    async def srpc__test(msg: EmptyMock) -> Res[Any]:
        return Ok(None)
    bus = ServerBus.ie()
    await bus.init()
    assert "test" in bus._rpckey_to_fn  # noqa: SLF001

async def test_reg_custom_rpc_key():
    async def srpc__test(msg: EmptyMock) -> Res[Any]:
        return Ok(None)
    bus = ServerBus.ie()
    await bus.init()
    bus.reg_rpc(srpc__test, "whocares").eject()
    assert "whocares" in bus._rpckey_to_fn  # noqa: SLF001
