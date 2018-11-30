from typing import List

from pandas import Series

from comopt.data_structures.usef_message_types import FlexRequest
from comopt.model.ems import EMS
from comopt.model.utils import initialize_series


def equal_flex_split_requested(
    ems_agents: List[EMS], flex_request: FlexRequest, environment,
) -> Series:
    """Split up the requested values in the FlexRequest equally amongst the EMS agents."""
    #TODO: Get flex absolute without calling market_agent directly
    flex_absolute = environment.market_agent.balancing_opportunities["Imbalance (in MW)"]

    flex_absolute = initialize_series(
                    data=[
                        value / len(ems_agents)
                        for value in flex_absolute[flex_request.start:flex_request.end-flex_request.resolution].values
                    ],
                    start=flex_request.start,
                    end=flex_request.end,
                    resolution=flex_request.resolution,
                )

    flex_relative = initialize_series(
                    data=[
                        value / len(ems_agents)
                        for value in flex_request.commitment.constants.values
                    ],
                    start=flex_request.start,
                    end=flex_request.end,
                    resolution=flex_request.resolution,
                )

    print("EQUAL FLEX SPLIT: {}".format(flex_absolute.values))

    return {"target_power":flex_relative, "target_flex":flex_absolute}


def implement_your_own_flex_split_method_here(
    ems_agents: List[EMS], flex_request: FlexRequest
) -> Series:
    """Todoc: write docstring."""
    return initialize_series(
        data=flex_request.commitment.constants.values,
        start=flex_request.start,
        end=flex_request.end,
        resolution=flex_request.resolution,
    )
