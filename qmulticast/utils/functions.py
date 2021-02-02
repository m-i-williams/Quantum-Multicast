"""Helper functions."""

# define a generic GHZ
import logging

import numpy as np
from netsquid.nodes import Node
from netsquid.qubits.qubitapi import fidelity, reduced_dm
from netsquid.qubits.qrepr import convert_to 
from netsquid.qubits.dmtools import DMRepr
from netsquid.util.simtools import sim_time

logger = logging.getLogger(__name__)


def gen_GHZ_ket(n) -> np.ndarray:
    """Create a GHZ state of n qubits.

    Parameters
    ----------
    n : int
        The number of qubits.
    """
    k = 2 ** n
    x = np.zeros((k, 1), dtype=complex)
    x[k - 1] = 1
    x[0] = 1
    # return = KetRepr(x)/np.sqrt(2)
    return x / np.sqrt(2)


def fidelity_from_node(source: Node) -> float:
    """Calculate the fidelity of GHZ state creation.

    Parameters
    ----------
    node : Node
        The node object to treat as source.
    """
    logger.debug(f"Calculating fidelity of GHZ state from source {source}")

    network = source.supercomponent

    edges = [
        name.lstrip("qsource-")
        for name in source.subcomponents.keys()
        if "qsource" in name
    ]
    recievers = {edge.split("-")[-1]: edge for edge in edges}

    qubits = []
    for node in network.nodes.values():
        if node is source:
            # Assume that the source has a qubit
            # and that it's in the 0 position.
            qubits += node.qmemory.peek(0)

        if node.name in recievers:
            mem_pos = node.qmemory.get_matching_qubits(
                "edge", value=recievers[node.name]
            )
            qubits += node.qmemory.peek(mem_pos)
    
    # Bit ugly this walrus but I haven't been able to
    # use it yet and I think it's cute.
    if (lq:= len(qubits)) - (le:= len(edges)) != 1:
        logger.warning("Looks like some GHZ qubits were lost!")
        logger.warning("Number of edges: %s", lq)
        logger.warning("Number of qubits: %s", le)

    logger.debug("GHZ Qubit(s) %s", qubits)
    fidelity_val = fidelity(qubits, gen_GHZ_ket(len(qubits)), squared=True)
    #dm = convert_to(qubits, DMRepr)
    logger.info(f"Fidelity: {fidelity_val}")
    logger.info(f"Reduced dm of qubits: \n{reduced_dm(qubits)}")

def log_entanglement_rate():
    """Generator to find the entanglement rate."""
    vals = [sim_time()]
    logger.info("Entanglement rate initialised.")
    yield

    while True:
        vals.append(sim_time())
        diff = vals[-1] - vals[-2]
        if diff == 0:
            logger.error("No time has passed - entanglement rate infinite.")
        else:
            logger.info(f"Entanglement Rate: {1/diff}Hz")
        yield
