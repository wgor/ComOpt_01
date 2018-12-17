from datetime import datetime, timedelta
from random import uniform, randint, gauss, seed

from pandas import set_option

from comopt.model.environment import Environment
from comopt.scenario.balancing_opportunities import (
    single_curtailment_each_day_from_hours_a_to_b,
    single_curtailment_or_shift_each_day_from_hours_a_to_b,
    generated_imbalance_profile,
)

from comopt.scenario.battery_constraints import limited_battery_capacity_profile
from comopt.scenario.profile_generator import pickle_profiles
from comopt.scenario.ems_constraints import (
    limited_capacity_profile as grid_connection,
    follow_generated_consumption_profile,
    follow_generated_production_profile,
    follow_solar_profile,
    curtailable_solar_profile,
    curtailable_integer_test_profile,
    follow_integer_test_profile,
    dispatchable_load_profile_with_bounds
    # curtailable_integer_test_profile,
)

# POLICY FUNCTIONS:
from comopt.scenario.ma_policies import (
    never_buy,
    buy_at_any_cost,
    buy_with_deterministic_prices,
    buy_with_stochastic_prices,
)
from comopt.scenario.ta_policies import (
    never_sell,
    sell_at_any_cost,
    sell_with_deterministic_prices,
    sell_with_stochastic_prices,
    Q_learning,
)

# TA Q-LEARNING EXPLORATION FUNCTIONS:
from comopt.scenario.ta_policies import (
    choose_action_randomly_using_uniform,
    choose_action_greedily_with_noise,
)

# TA Q-LEARNING ACTION FUNCTIONS:
from comopt.scenario.ta_policies import multiply_markup_evenly

# Concession and Noise Curves:
from comopt.model.utils import (
    initialize_series,
    initialize_index,
    linear,
    root_divided_by_2,
    cos_root_divided_by_2,
    no_shape,
    uniform_1,
    gauss_1,
    gauss_2,
    no_noise,
)
from comopt.utils import save_env
from comopt.plotting.negotiation_plots import plot_negotiation_data
from comopt.plotting.profile_plots import (
    plot_ems_data,
    plot_ma_data,
    plot_ems_net_demand_data,
)

# Set horizon
start = datetime(year=2018, month=6, day=1, hour=12)
end = datetime(year=2018, month=6, day=1, hour=16)
resolution = timedelta(minutes=15)

# --------------PICKLE PROFILES---------------#
pickled_profiles = pickle_profiles(start=start, end=end, resolution=resolution)
imbalances_test_profile_1_day = pickled_profiles["imbalances_test_profile_1_day"]
imbalance_prices_test_profile_1_day = pickled_profiles[
    "imbalance_prices_test_profile_1_day"
]
solar_test_profile_1_day = pickled_profiles["solar_test_profile_1_day"]
load_test_profile_1_day = pickled_profiles["load_test_profile_1_day"]
deviation_prices = pickled_profiles["deviation_prices"]
purchase_price = pickled_profiles["purchase_price"]
feed_in_price = pickled_profiles["feed_in_price"]
imbalance_market_costs = pickled_profiles["imbalance_market_costs"]
flexible_load_profile = pickled_profiles["flexible_load_profile"]
net_demand_without_flex = pickled_profiles["net_demand_without_flex"]
net_demand_costs_without_flex = pickled_profiles["net_demand_costs_without_flex"]

dispatch_factor_load = 0.25
dispatch_factor_solar = 1
deviation_multiplicator = 1

imbalances_test_profile_1_day[:] = 2
solar_test_profile_1_day[:] = 0

deviation_prices[:] = imbalance_prices_test_profile_1_day * 1.2
# for e,idx in enumerate(imbalances_test_profile_1_day.index):
#     if e % 4 == 0:
#         imbalances_test_profile_1_day.loc[idx] = -2


# ------------OPTIONAL END-------------#
input_data = {
    # Optimization Input Parameter:
    "Seed": seed(111),
    "Balancing opportunities":
    # single_curtailment_or_shift_each_day_from_hours_a_to_b(start=start, end=end, resolution=resolution, a=10, b=12),
    # single_curtailment_or_shift_each_day_from_hours_a_to_b(start=start, end=end, resolution=resolution, a=12, b=14),
    generated_imbalance_profile(
        start=start,
        end=end,
        resolution=resolution,
        imbalance_range=(0, 5),
        imbalance_price_1=10,
        imbalance_price_2=8,
        frequency=1,
        window_size=(1, 10),
        imbalance_profile=imbalances_test_profile_1_day,
        imbalance_prices=imbalance_prices_test_profile_1_day,
    ),
    "EMS constraints": [
        grid_connection(start=start, end=end, resolution=resolution, capacity=100),  # Todo: List should have the same length as the number of EMSs
    ],
    "Device constraints": [
        # Profilenames need to contain "consumption", "generation", "battery", "buffer" as keywords for the plotting function!
        [  # >>>>>> EMS 1 <<<<<#
            # 1) Load
            # follow_generated_consumption_profile(start=start, end=end, resolution=resolution,
            # max_capacity=10, dispatch_factor=dispatch_factor_load, profile=load_test_profile_1_day),
            (
                "load",
                dispatchable_load_profile_with_bounds(
                    start=start,
                    end=end,
                    resolution=resolution,
                    profile=flexible_load_profile,
                ),
            ),
            # 2) Generation
            (
                "generator",
                follow_generated_production_profile(
                    start=start,
                    end=end,
                    resolution=resolution,
                    max_capacity=10,
                    dispatch_factor=dispatch_factor_solar,
                    profile=solar_test_profile_1_day,
                ),
            ),
            # curtailable_integer_solar_profile(start=start, end=end, resolution=resolution)
            # 3) Battery
            # limited_battery_capacity_profile(start=start, end=end, resolution=resolution,
            #                                 battery_power_capacity=5, soc_limits=(5,20), soc_start=10,)
            # 4) Buffer
        ],
        [],  # >>>>>> EMS 2 <<<<<#
        [],  # >>>>>> EMS 3 <<<<<#
    ],  # Devices is a list, where each item is a device (we haven't got a class for devices, so a device is just a tuple with a device type name and a constraints dataframe)
    # self.gradient_down = gradient[0] * flow_unit_multiplier
    "EMS prices": [(feed_in_price, purchase_price), (feed_in_price, purchase_price), (feed_in_price, purchase_price)],
    "MA deviation prices": deviation_prices,
    "MA deviation multiplicator": deviation_multiplicator,  # can be used to increase the deviation prices in each step
    "MA imbalance market costs": imbalance_market_costs,
    "Central optimization": False,
    "MA horizon": timedelta(hours=1),
    "TA horizon": timedelta(hours=1),
    "Step_now": 0,
    # Prognosis negotiation parameter
    "Prognosis rounds": 10,
    "MA prognosis policy": buy_with_stochastic_prices,
    # MA POLICIES:
    # never_buy
    # buy_at_any_cost
    # buy_with_deterministic_prices
    # buy_with_stochastic_prices
    "MA prognosis parameter": {
        "reservation_price": 4,
        "markup": 1,
        "concession": root_divided_by_2,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
    },
    "TA prognosis policy": sell_with_stochastic_prices,
    # TA POLICIES:
    # never_sell,
    # sell_at_any_cost,
    # sell_with_deterministic_prices,
    # sell_with_stochastic_prices,
    # Q_learning
    "TA prognosis parameter": {
        "reservation_price": 2,
        "markup": 1,
        "concession": linear,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
    },
    "Q parameter prognosis": {
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        # TA EXP FUNCS:# multiply_markup_evenly
        "Exploration function": choose_action_randomly_using_uniform,
        # TA ACT FUNCS: # choose_action_greedily_with_noise
        # choose_action_randomly_using_uniform
        "Step now": 0,
    },
    # Flexrequest negotiation parameter
    "Flexrequest rounds": 10,
    "MA flexrequest policy": buy_with_stochastic_prices,
    # MA POLICIES:
    # never_buy
    # buy_at_any_cost
    # buy_with_deterministic_prices
    # buy_with_stochastic_prices
    "MA flexrequest parameter": {
        "reservation_price": 6.5,  # Placeholder variable
        "reservation_price_factor": 2,
        "markup": 1,  # Placeholder variable
        "markup_factor": 1,
        "concession": linear,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "noise": no_noise,  #  uniform_1, gauss_1, gauss_2, no_noise
        "Sticking factor": 0,  # Close to 0 means little sticking request, close to 1 means a lot of sticking requests
    },
    "TA flexrequest policy": sell_with_stochastic_prices,
    # TA POLICIES:
    # never_sell,
    # sell_at_any_cost,
    # sell_with_deterministic_prices,
    # sell_with_stochastic_prices,
    # Q_learning
    "TA flexrequest parameter": {
        "reservation_price": 6,  # Placeholder variable
        "reservation_deviation_price": 0,  # Placeholder variable
        "markup_factor": 1,
        "markup": 1,  # Placeholder variable
        "concession": no_shape,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "noise": no_noise,  # #  uniform_1, gauss_1, gauss_2, no_noise
    },
    "Q parameter flexrequest": {
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        # TA EXP FUNCS:# multiply_markup_evenly
        "Exploration function": choose_action_randomly_using_uniform,
        # TA ACT FUNCS: # choose_action_greedily_with_noise
        # choose_action_randomly_using_uniform
        "Step now": 0,
    },
}

# Set up simulation environment
env = Environment(
    name="Baseline scenario without any FlexRequests.",
    start=start,
    end=end,
    resolution=resolution,
    input_data=input_data,
)

# Run simulation model
env.run_model()

# Save simulation results
save_env(env)

# Analyse simulation results
plot_ma_data(env)
plot_ems_data(env)
# plot_ems_net_demand_data(env)
env.ems_agents[0].realised_power_per_device.plot()
env.ems_agents[0].planned_power_per_device.plot()

env.ems_agents[0].realised_flex_per_device
env.trading_agent.cleared_flex_negotiations
# %%

plt_2 = plot_negotiation_data(
    negotiation_data_df=env.plan_board.flexrequest_negotiation_log_1,
    q_tables=env.trading_agent.stored_q_tables_flexrequest_1,
    action_tables=env.trading_agent.stored_action_tables_flexrequest_1,
    input_data=input_data,
)

# plt_1 = plot_negotiation_data(negotiation_data_df=env.plan_board.prognosis_negotiation_log_1,
#                       q_tables=env.trading_agent.stored_q_tables_prognosis_1,
#                       action_tables=env.trading_agent.stored_action_tables_prognosis_1,
#                       input_data = input_data,
#                       )
# %%
