# Copyright (c) 2022 The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from pathlib import Path
from typing import (
    List,
    Tuple,
)

from m5.util import (
    fatal,
    warn,
)

from gem5.resources.resource import SimpointResource


class SimPoint:
    """
    This SimPoint class is used to manage the information needed for SimPoints
    in workload.

    """

    def __init__(
        self,
        simpoint_interval: int,
        simpoint_resource: SimpointResource | None = None,
        simpoint_file_path: Path | None = None,
        weight_file_path: Path | None = None,
        simpoint_list: List[int] | None = None,
        weight_list: List[float] | None = None,
        warmup_interval: int = 0,
    ) -> None:
        """
        :param simpoint_interval: The length of each SimPoints interval.
        :param simpoint_file_path: The path to the SimPoints result file
                                   generated by Simpoint3.2 or gem5.
        :param weight_file_path: The path to the weight result file generated
                                         by Simpoint3.2 or gem5.

        :param simpoint_list: A list of SimPoints starting instructions.
        :param weight_list: A list of SimPoints weights.
        :param warmup_interval: A number of instructions for warming up before
                                restoring a SimPoints checkpoint.

        .. note::

            Need to pass in the paths or the lists for the SimPoints and their
            weights. If the paths are passed in, no actions will be done to the
            list.

            When passing in ``simpoint_list`` and ``weight_list``, passing in sorted lists
            (sorted by SimPoints in ascending order) is strongly suggested.
            The ``warmup_list`` only works correctly with sorted ``simpoint_list``.
        """

        warn(
            "This SimPoint class has been deprecated in favor of "
            "`SimpointResource` and `SimpointDirectory` resource which may be "
            "found in `gem5.resources.resource`. Please utilize these. This "
            "SimPoint class will be removed in future releases of gem5."
        )

        # initalize input if you're passing in a CustomResource
        if simpoint_resource is not None:
            # TODO: Refactor this block
            simpoint_directory = str(simpoint_resource.get_local_path())

            simpoint_file_path = simpoint_directory.get_simpoint_file()
            weight_file_path = simpoint_resource.get_weight_file()
            simpoint_interval = simpoint_resource.get_metadata().get(
                "simpoint_interval"
            )
            warmup_interval = simpoint_resource.get_metadata().get(
                "warmup_interval"
            )

        self._simpoint_interval = simpoint_interval

        if simpoint_file_path is None or weight_file_path is None:
            if simpoint_list is None or weight_list is None:
                fatal(
                    "Please pass in file paths or lists for both simpoints "
                    "and weights."
                )
            else:
                self._simpoint_start_insts = list(
                    inst * simpoint_interval for inst in simpoint_list
                )
                self._weight_list = weight_list
        else:
            # if passing in file paths then it calls the function to generate
            # simpoint_start_insts and weight list from the files
            (
                self._simpoint_start_insts,
                self._weight_list,
            ) = self.get_weights_and_simpoints_from_file(
                simpoint_file_path, weight_file_path
            )

        if warmup_interval != 0:
            self._warmup_list = self.set_warmup_intervals(warmup_interval)
        else:
            self._warmup_list = [0] * len(self._simpoint_start_insts)

    def get_weights_and_simpoints_from_file(
        self,
        simpoint_path: Path,
        weight_path: Path,
    ) -> Tuple[List[int], List[float]]:
        """
        This function takes in file paths and outputs a list of SimPoints
        instruction starts and a list of weights.
        """
        simpoint = []
        with open(simpoint_path) as simpoint_file, open(
            weight_path
        ) as weight_file:
            while True:
                line = simpoint_file.readline()
                if not line:
                    break
                interval = int(line.split(" ", 1)[0])
                line = weight_file.readline()
                if not line:
                    fatal("not engough weights")
                weight = float(line.split(" ", 1)[0])
                simpoint.append((interval, weight))
        simpoint.sort(key=lambda obj: obj[0])
        # use simpoint to sort
        simpoint_start_insts = []
        weight_list = []
        for start, weight in simpoint:
            simpoint_start_insts.append(start * self._simpoint_interval)
            weight_list.append(weight)
        return simpoint_start_insts, weight_list

    def set_warmup_intervals(self, warmup_interval: int) -> List[int]:
        """
        This function takes the ``warmup_interval``, fits it into the
        ``_simpoint_start_insts``, and outputs a list of warmup instruction lengths
        for each SimPoint.

        The warmup instruction length is calculated using the starting
        instruction of a SimPoint to minus the ``warmup_interval`` and the ending
        instruction of the last SimPoint. If it is less than 0, then the warmup
        instruction length is the gap between the starting instruction of a
        SimPoint and the ending instruction of the last SimPoint.
        """
        warmup_list = []
        for index, start_inst in enumerate(self._simpoint_start_insts):
            warmup_inst = start_inst - warmup_interval
            if warmup_inst < 0:
                warmup_inst = start_inst
            else:
                warmup_inst = warmup_interval
            warmup_list.append(warmup_inst)
            # change the starting instruction of a SimPoint to include the
            # warmup instruction length
            self._simpoint_start_insts[index] = start_inst - warmup_inst
        return warmup_list

    def get_simpoint_start_insts(self) -> List[int]:
        return self._simpoint_start_insts

    def get_weight_list(self) -> List[float]:
        return self._weight_list

    def get_simpoint_interval(self) -> int:
        return self._simpoint_interval

    def get_warmup_list(self) -> List[int]:
        return self._warmup_list
