from datetime import datetime, timedelta
from math import sqrt, sin, nan
from pandas import (
    DataFrame, MultiIndex, IndexSlice, Index, set_option, plotting,
    concat, date_range, option_context, to_numeric, isnull,
    )
from comopt.model.environment import Environment
from comopt.scenario.balancing_opportunities import (
    single_curtailment_each_day_between_2_and_3_am,
    single_curtailment_or_shift_each_day_between_10_and_12_am,
    single_curtailment_or_shift_each_day_between_12_and_14_pm,
    generated_imbalance_profile,
)

from comopt.scenario.battery_constraints import limited_battery_capacity_profile
from comopt.scenario.buffer_constraints import follow_generated_buffer_profile
from comopt.scenario.profile_generator import pickle_profiles
from comopt.scenario.ems_constraints import (
    limited_capacity_profile as grid_connection,
    follow_generated_consumption_profile,
    follow_generated_production_profile,
    follow_solar_profile,
    curtailable_solar_profile,
    curtailable_integer_solar_profile,
    follow_integer_test_profile,
    dispatchable_load_profile_with_bounds
    # curtailable_integer_test_profile,
)

# POLICY FUNCTIONS:
from comopt.policies.ma_policies import (
    never_buy,
    buy_at_any_cost,
    buy_with_deterministic_prices,
    buy_with_stochastic_prices,
)
from comopt.policies.ta_policies import (
    never_sell,
    sell_at_any_cost,
    sell_with_deterministic_prices,
    sell_with_stochastic_prices,
    Q_learning,
)

# TA Q-LEARNING:
from comopt.policies.adaptive_strategies import (
    choose_action_randomly_using_uniform,
    choose_action_greedily_with_noise,
    multiply_markup_evenly
)

# Concession and Noise Curves:
from comopt.model.negotiation_utils import (
    linear, root_divided_by_2, cos_root_divided_by_2, no_shape,
    uniform_1, gauss_1, gauss_2, no_noise,
)
from comopt.model.utils import (
    initialize_series, initialize_index
)
from comopt.utils import data_import
from comopt.plotting.negotiation_plots import plot_negotiation_data
from comopt.plotting.profile_plots import (
    plot_ems_data,
    plot_ma_data,
    plot_ems_net_demand_data,
)

import time
from random import uniform, randint, gauss, seed
from copy import deepcopy
import matplotlib.pyplot as plt
import pickle
import numpy as np
from pandas import Series

# Console output configuration

set_option("display.max_columns", 100)
set_option("column_space", 5)
set_option("display.max_colwidth", 150)
set_option("display.width", 320)
set_option("display.large_repr", "truncate")
# set_option("multi_sparse", True)
set_option("date_dayfirst", True)
set_option("display.precision", 2)
# set_option('expand_frame_repr', True)
set_option('precision', 5)

logfile = open('simulation_logfile.txt', 'w')

# Set horizon
start_time = time.time()
start = datetime(year=2018, month=6, day=1, hour=0)
end = datetime(year=2018, month=6, day=1, hour=2)
resolution = timedelta(minutes=15)

# Set EMS agents
number_of_agents = 1
ems_names = []
for number in range(1, number_of_agents + 1):
    ems_name = "EMS " + str(number)
    ems_names.append(ems_name)

# --------------PICKLE PROFILES---------------#
# Get pickled profiles
pickled_profiles = pickle_profiles(start=start, end=end, resolution=resolution)

# MA: Imbalances
imbalances_test_profile_1_day = pickled_profiles["imbalances_test_profile_1_day"]

# MA: Up/down regulation prices on outside markets
imbalance_prices_test_profile_1_day = pickled_profiles["imbalance_prices_test_profile_1_day"]
imbalance_prices_test_profile_1_day=deepcopy(imbalances_test_profile_1_day)

# MA: Prices for deviating from commitments
deviation_prices = pickled_profiles["deviation_prices"]

# EMS: PV-Production
solar_test_profile_1_day = pickled_profiles["solar_test_profile_1_day"]
solar_test_profile_1_day[:] = 7

# EMS: Unflexbible Load
load_test_profile_1_day = pickled_profiles["load_test_profile_1_day"]

# EMS: Load that can be switched per control signal
flexible_load_profile = pickled_profiles["flexible_load_profile"]

# EMS: Energy contract prices for receiving energy from the grid
purchase_price = pickled_profiles["purchase_price"]

# EMS: Energy contract prices for feeding in energy to the grid
feed_in_price = pickled_profiles["feed_in_price"]

imbalance_market_costs = pickled_profiles["imbalance_market_costs"]

net_demand_without_flex = pickled_profiles["net_demand_without_flex"]
net_demand_costs_without_flex = pickled_profiles["net_demand_costs_without_flex"]

dispatch_factor_load = 0.25
dispatch_factor_solar = 1
deviation_multiplicator = 1

imbalance_prices_test_profile_1_day[:] = 50
imbalances_test_profile_1_day=round(imbalances_test_profile_1_day, 1)
imbalances_test_profile_1_day = abs(imbalances_test_profile_1_day)
imbalances_test_profile_1_day[:] = 10
# imbalances_test_profile_1_day[2] = 10
# imbalances_test_profile_1_day[3] = 15
# imbalances_test_profile_1_day[4] = 20
imbalances_test_profile_1_day
imbalance_prices_test_profile_1_day
deviation_prices = imbalance_prices_test_profile_1_day + 10

pickle_off = open("comopt/pickles/buffer_2hours_2windows.pickle", "rb")
buffer_2hours_2windows = pickle.load(pickle_off)
buffer_2hours_2windows.iloc[-1, -2] = 10
buffer_2hours_2windows.iloc[-1, -1] = 0
buffer_2hours_2windows.iloc[3:5, -2:] = 0
buffer_2hours_2windows
# deviation_prices[1] = 0
# imbalance_prices_test_profile_1_day
# deviation_prices

# df = follow_generated_buffer_profile(start=start, end=end, resolution=resolution,
#                                 buffer_power_capacity=5,
#                                 frequency=0.5,
#                                 window_size=3,
#                                 soc_limits=(5,20),
#                                 soc_start=10
# ),
#
# df
# df = follow_generated_buffer_profile(start=start, end=end, resolution=resolution,
#                                      buffer_power_capacity=10,
#                                      fraction=0.25)
#
# df.loc[:]=nan
# df

# pickling_on = open("buffer_2hours_2windows.pickle","wb")
# pickle.dump(df, pickling_on)
# pickling_on.close()
# df['height'] = df["derivative max"]
# df['height'].loc[df["height"] > 0]

# plt.bar(x=df.index, height=df['derivative max'], width=0.01)
imbalance_prices_test_profile_1_day
# for e,idx in enumerate(imbalances_test_profile_1_day.index):
#     if e % 4 == 0:
#         imbalances_test_profile_1_day.loc[idx] = -2
flex_price = 10
# ------------OPTIONAL END-------------#
input_data = {
    # Optimiziation Input Parameter:
    "Seed": seed(111),
    "Logfile": logfile,
    # TODO: Find all Flow multipliers and replace it with the input data
    "Flow unit multiplier": resolution.seconds / 3600,
    "Balancing opportunities":
    # single_curtailment_or_shift_each_day_between_10_and_12_am(start=start, end=end, resolution=resolution),
    # single_curtailment_or_shift_each_day_between_12_and_14_pm(start=start, end=end, resolution=resolution),
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
        grid_connection(start=start, end=end, resolution=resolution, capacity=100)
    ],
    "Devices": [
        # Profilenames need to contain "consumption", "generation", "battery", "buffer" as keywords for the plotting function!
        [  # >>>>>> EMS 1 <<<<<#
            # 1) Load
            # (
            #     "Load",
            #     dispatchable_load_profile_with_bounds(
            #         start=start,
            #         end=end,
            #         resolution=resolution,
            #         profile=flexible_load_profile,
            #     ),
            # ),
            # # 2) Generation
            # (
            #     "Generator",
            #     follow_generated_production_profile(
            #         start=start,
            #         end=end,
            #         resolution=resolution,
            #         max_capacity=10,
            #         dispatch_factor=dispatch_factor_solar,
            #         profile=solar_test_profile_1_day,
            #     ),
            # ),
            # curtailable_integer_solar_profile(start=start, end=end, resolution=resolution)
            # 3) Battery
            # (
            #     "Battery",
            #     limited_battery_capacity_profile(start=start, end=end, resolution=resolution,
            #                                     battery_power_capacity=5, soc_limits=(5,20), soc_start=10
            #     ),
            # ),
            # 4) Buffer
            (
                "Buffer", buffer_2hours_2windows
                # follow_generated_buffer_profile(start=start, end=end, resolution=resolution,
                #                                 buffer_power_capacity=10,
                #                                 fraction=0.25,
                # ),
            ),

        ],
        [],  # >>>>>> EMS 2 <<<<<#y
        [],  # >>>>>> EMS 3 <<<<<#
    ],  # Devices is a list, where each item is a device (we haven't got a class for devices, so a device is just a tuple with a device type name and a constraints dataframe)
    # self.gradient_down = gradient[0] * flow_unit_multiplier
    "EMS prices": [(feed_in_price, purchase_price, flex_price)],
    # "MA imbalance_market_costs": imbalance_market_costs,
    "Central optimization": False,
    "MA horizon": timedelta(hours=1),
    "TA horizon": timedelta(hours=1),
    # "Timestep now": 0,

    # Prognosis negotiaton parameter

    "MA prognosis parameter": {
        "Policy": buy_with_stochastic_prices,
        "Reservation price": 4,
        "Markup": 1,
        "Concession": root_divided_by_2,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
    },

    "TA prognosis parameter": {
        "Policy": Q_learning, # never_sell, sell_at_any_cost, sell_with_deterministic_prices, sell_with_stochastic_prices, Q_learning,
        "Negotiation rounds": 10,
        "Reservation price": 2,
        "Markup": 1,
        "Concession": linear,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
        # "Adaptive strategy": Q-learning,
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        "Exploration function": choose_action_randomly_using_uniform,
        "Step now": 1, # Used in Q-Learing exploration function
    },

    # Flexrequest negotiaton parameter

    "MA flexrequest parameter": {
        "Policy": buy_with_stochastic_prices,
        "Reservation price": 6.5,  # Placeholder variable
        "Deviation prices": deviation_prices,
        "Markup": 1,  # Placeholder variable
        "Concession": linear,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": no_noise,  #  uniform_1, gauss_1, gauss_2, no_noise
        "Sticking factor": 0,  # 0: no "sticking" requests, 1: only sticking requests
    },

    "TA flexrequest parameter": {
        "Policy": Q_learning,
        "Negotiation rounds": 10,
        "Reservation price": 0,  # Placeholder value
        "Markup": 1,  # Placeholder variable
        "Concession": no_shape,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": no_noise,  # #  uniform_1, gauss_1, gauss_2, no_noise
        # "Adaptive strategy": None, # Simple, Hill-Climbing, Q-Learning
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        "Exploration function": choose_action_randomly_using_uniform,
        "Step now": 1,
    },
}

# Set up simulation environment
env = Environment(
    name="Baseline scenario without any FlexRequests.",
    start=start,
    end=end,
    resolution=resolution,
    ems_names=ems_names,
    input_data=input_data,
)

# pickling_on = open("2hours_cleared_simple_res_prices.pickle","wb")
# pickle.dump(env, pickling_on)
# pickling_on.close()

# Run simulation model
env.run_model()
# execution time i minutes
execution_time = (time.time() - start_time) / 60
execution_time
# Cut off head and tail for analysis
cut_head = timedelta(days=1)
cut_tail = timedelta(days=1)
analysis_window = (env.start + cut_head, env.end - env.resolution - cut_tail)

# Analyse simulation results

# %%
plot_ma_data(env)
# %%
plot_ems_data(env)
# %%
plot_ems_net_demand_data(env)
# %%
env.market_agent.commitment_data
env.ems_agents[0].realised_power_per_device.plot()
env.ems_agents[0].planned_power_per_device.plot()

env.ems_agents[0].realised_flex_per_device
env.trading_agent.cleared_flex_negotiations
# %%

plt_2 = plot_negotiation_data(
    negotiation_data=env.plan_board.flexrequest_negotiation_log_1,
    q_tables=env.trading_agent.stored_q_tables_flexrequest_1,
    action_tables=env.trading_agent.stored_action_tables_flexrequest_1,
    input_data=input_data,
)

# plt_1 = plot_negotiation_data(negotiation_data=env.plan_board.prognosis_negotiation_log_1,
#                       q_tables=env.trading_agent.stored_q_tables_prognosis_1,
#                       action_tables=env.trading_agent.stored_action_tables_prognosis_1,
#                       input_data = input_data,
#                       )
# %%
# hierarchical indices and columns




# import pandas as pd
# index = pd.MultiIndex.from_product([[2013, 2014]],
#                                    names=['datetime'])
#
# columns = pd.MultiIndex.from_product([['load', 'generation', 'buffer'], ["a","b"]], ["Prognosed_power", "Planned_power", "Realized_power", "Prognosed_flex", "Planned_flex", "Realized_flex"]],
#                                      names=['Device', ''])
#
# # mock some data
# data = np.round(np.random.randn(4, 6), 1)
# data[:, ::2] *= 10
# data += 37
#
# # create the DataFrame
# health_data = pd.DataFrame(0, index=index, columns=columns)
# health_data
# #%%
#

#
# start = datetime(year=2018, month=6, day=1, hour=12)
# end = datetime(year=2018, month=6, day=1, hour=14)
# resolution = timedelta(minutes=15)
#
# create_data_log(start,end,resolution, [""])
