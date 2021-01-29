"""Defines the protocol to be followed at a node bipartite source(s)"""
import logging
import operator
from functools import reduce
from typing import Optional

from netsquid.components.instructions import INSTR_SWAP
from netsquid.nodes import Node
from netsquid.protocols import NodeProtocol
from netsquid.protocols.protocol import Signals
from netsquid.qubits.qubitapi import fidelity, reduced_dm

from qmulticast.programs import CreateGHZ
from qmulticast.protocols.report_input import MoveInput
from qmulticast.utils import gen_GHZ_ket

logger = logging.getLogger(__name__)

handler = logging.FileHandler(filename="fidelity-data.txt", mode="w")

res_logger = logging.Logger(name="results")
res_logger.addHandler(handler)


class BipartiteProtocol(NodeProtocol):
    """Class defining the protocol of a bipartite network node.

    If the node is a source, send out entangled qubits and transform to GHZ.
    If the node is a reciever, await incoming qubit and classical message.
    """

    def __init__(self, node: Node, name: Optional[str] = None, source: bool = False):
        """Initialise the protocol wiht information about the node.

        Parameters
        ----------
        node : Node
            The node on which to run this protocol.
        name : Optional[str]
            The name of this protocol.
        source : bool, default = True
            Whether this node should act as a source.
            If not the node is a reciever.
        """
        logger.debug(f"Initialising Bipartite protocol for node {node.name}.")
        super().__init__(node=node, name=name)

        self.input_ports = [port for port in self.node.qmemory.ports if "qin" in port]
        self.input_ports.remove("qin")
        self.input_ports = [
            port for port in self.input_ports if int(port.lstrip("qin")) % 2 == 1
        ]

        self.source_mem = [port for port in self.node.qmemory.ports if "qin" in port]

        self.source_mem.remove("qin")
        self.source_mem = [
            port for port in self.source_mem if int(port.lstrip("qin")) % 2 == 0
        ]

        self.output_ports = [
            port for port in self.node.ports.values() if "out" in port.name
        ]

        self._is_source = source
        self._mem_size = self.node.qmemory.num_positions

        # for port_num in range(self._mem_size):
        #     # We assume input memory ports are the odd numbers.
        #     if port_num % 2 == 1:
        #         logger.debug("Adding move protocol for port %s", port_num)
        #         self.add_subprotocol(
        #             MoveInput(self.node, node.qmemory.ports[f"qin{port_num}"])
        #         )

    def run(self):
        """Run the protocol."""
        node = self.node
        logger.debug(f"Running bipartite protocol on node {node.name}.")
        logger.debug(f"Node: {self.node.name} " + f"has {self._mem_size} memory slots.")

        while (counter := 0 < 1) :
            # Send from source.
            # - out to all connection ports.
            counter += 1
            if self._is_source:
                for port in self.output_ports:
                    logger.debug(f"Found port {port.name}")
                    edge = port.name.lstrip("out-")

                    # Trigger the source
                    source_name = "qsource-" + edge
                    self.node.subcomponents[source_name].trigger()
                    logger.debug(f"Triggered source {source_name}.")

                await_all_sources = [
                    self.await_port_input(self.node.qmemory.ports[port])
                    for port in self.source_mem
                ]
                yield reduce(operator.and_, await_all_sources)

                logger.debug("Got all memory input from sources.")
                # Do entanglement
                bell_qubits = [
                    pos for pos in self.node.qmemory.used_positions if pos % 2 == 0
                ]
                prog = CreateGHZ(bell_qubits)
                node.subcomponents["qmemory"].execute_program(prog)

                # import pdb; pdb.set_trace()
                qubits = [
                    self.node.qmemory.peek(pos)[0]
                    for pos in node.qmemory.used_positions
                ]
                fidelity_val = fidelity(qubits, gen_GHZ_ket(len(qubits)), squared=True)
                logger.debug(f"Fidelity: {fidelity_val}")
                logger.debug(f"Reduced dm of qubits: \n{reduced_dm(qubits)}")

                self.send_signal(Signals.SUCCESS, fidelity_val)

            if not self._is_source:
                # Get input
                await_any_input = [
                    self.await_port_input(self.node.qmemory.ports[port])
                    for port in self.input_ports
                ]
                await_all_signals = []
                # if self.node.name == "0":
                #     import pdb;pdb.set_trace()
                yield reduce(operator.or_, await_any_input)

                logger.debug(
                    f"Got input: memory useage {self.node.qmemory.used_positions}"
                )
                logger.debug(
                    f"Node {self.node.name} used memory: {self.node.qmemory.used_positions}"
                )
