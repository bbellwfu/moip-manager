"""Source switching API routes."""
from fastapi import APIRouter, HTTPException

import config
from moip import MoIPClient
from moip.models import SwitchRequest, RoutingEntry

router = APIRouter()


def get_telnet_client() -> MoIPClient:
    """Get a MoIP telnet client."""
    return MoIPClient(config.MOIP_HOST, config.MOIP_TELNET_PORT)


@router.get("/routing", response_model=list[RoutingEntry])
async def get_routing():
    """Get current Tx->Rx routing assignments."""
    client = get_telnet_client()
    try:
        return client.get_routing()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch")
async def switch_source(request: SwitchRequest):
    """Switch a receiver to a transmitter source."""
    client = get_telnet_client()
    try:
        success = client.switch(request.tx, request.rx)
        if success:
            return {"success": True, "tx": request.tx, "rx": request.rx}
        else:
            raise HTTPException(status_code=500, detail="Switch command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unassign/{rx_id}")
async def unassign_receiver(rx_id: int):
    """Unassign a receiver (set to no source)."""
    client = get_telnet_client()
    try:
        # Switch to tx=0 to unassign
        success = client.switch(0, rx_id)
        if success:
            return {"success": True, "rx_id": rx_id}
        else:
            raise HTTPException(status_code=500, detail="Unassign command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
