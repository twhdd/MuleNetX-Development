from fastapi import APIRouter

from intelligence_core.simulations.fraud_ring import create_ring
from intelligence_core.simulations.layering_chain import create_layering_chain
from intelligence_core.simulations.mule_network import create_mule_network
from intelligence_core.simulations.smurfing import create_smurfing_attack

router = APIRouter()


@router.post("/simulate/mule")
def mule():

    return {
        "hub":
        create_mule_network()
    }


@router.post("/simulate/smurfing")
def smurfing():

    return {
        "destination":
        create_smurfing_attack()
    }


@router.post("/simulate/layering")
def layering():

    return {
        "chain":
        create_layering_chain()
    }


@router.post("/simulate/ring")
def ring():

    return {
        "ring":
        create_ring()
    }
