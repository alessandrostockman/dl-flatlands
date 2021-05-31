import itertools
import json
from datetime import datetime
from collections import deque

from abc import ABC, abstractmethod
import numpy as np

import tensorflow as tf
from tensorboard.plugins.hparams import api as hp
import wandb

class Logger(ABC):

    def __init__(self, base_dir, parameters, tuning=False):
        self._attributes = parameters['attributes']
        self._base_dir = base_dir
        self._log_dir = parameters['log_dir'] + "/" + self._get_driver_dir()
        self._hp_tuning = tuning

        if self._hp_tuning:
            self._hp_dir = parameters['hp_dir']
            self._hp_params_filename = parameters['hp_params_filename']
            self._init_hp()
    
    @abstractmethod
    def episode_start(self):
        pass
    
    @abstractmethod
    def episode_end(self, params, scores, episode_idx):
        pass

    @abstractmethod
    def get_run_params(self):
        pass
        
    @abstractmethod
    def log_step(self, pack, idx):
        pass

    @abstractmethod
    def log_episode(self, pack, idx):
        pass

    @abstractmethod
    def _log(self, pack, type, idx):
        pass

    @abstractmethod
    def _init_hp(self):
        pass

    @abstractmethod
    def _get_driver_dir(self):
        pass

class TensorboardLogger(Logger):

    def episode_start(self, run_params):
        self._run_dir = datetime.now().strftime("%Y%m%d-%H%M%S")

        self._windows = {}
        for attr in self._attributes.keys():
            if "avg" in self._attributes[attr]:
                self._windows[attr] = deque(maxlen=100)

    def episode_end(self, params, scores, episode_idx):
        if self._hp_tuning:
            with tf.summary.create_file_writer(self._base_dir + self._log_dir + '/' + self._hp_dir + '/' + self._run_dir).as_default():
                hp.hparams(dict(zip(self._hparams, params.values())))
                tf.summary.scalar('scores', scores, step=episode_idx)

    def get_run_params(self):
        if self._hp_tuning:
            return self._combinations
        else:
            return [{}]

    def log_step(self, pack, idx):
        self._log(pack, "step", idx) #TODO: Check if useful

    def log_episode(self, pack, idx):
        self._log(pack, "epsd", idx)

    def get_window(self, key):
        return self._windows[key]

    def _log(self, pack, type, idx):
        for attr, val in pack.items():
            if val is not None:
            
                with tf.summary.create_file_writer(self._base_dir + self._log_dir + '/' + self._run_dir).as_default():
                    if "val" in self._attributes[attr]:
                        tf.summary.scalar(attr + "_val", val, step=idx)
                    if "avg" in self._attributes[attr]:
                        self._windows[attr].append(val)
                        tf.summary.scalar(attr + "_avg", np.mean(self._windows[attr]), step=idx)

    def _init_hp(self):
        self._load_hp()
        self._metric = hp.Metric('scores') #TODO: Check if more metrics are needed
        # hp.Metric("epoch_accuracy",group="validation",display_name="accuracy (val.)",),
        # hp.Metric("epoch_loss",group="validation",display_name="loss (val.)",),
        # hp.Metric("batch_accuracy",group="train",display_name="accuracy (train)",), 
        # hp.Metric("batch_loss", group="train", display_name="loss (train)",)

        with tf.summary.create_file_writer(self._base_dir + self._log_dir + '/' + self._hp_dir).as_default():
            hp.hparams_config(
                hparams=self._hparams,
                metrics=[self._metric],
            )

    def _load_hp(self):
        self._hparams = []
        self._parameter_list = {}
        self._combinations = []
        with open(self._base_dir + self._hp_params_filename) as json_file:
            hyper_params = json.load(json_file)
            for key, descr in hyper_params.items():
                if descr['type'] == 'discrete':
                    hp_val = hp.Discrete(descr['values'])
                    hp_obj = hp.HParam(key, hp_val)
                    self._parameter_list[key] = hp_obj.domain.values
                elif descr['type'] == 'interval_real':
                    hp_val = hp.RealInterval(descr['min'], descr['max'])
                    hp_obj = hp.HParam(key, hp_val)
                    self._parameter_list[key] = tf.linspace(hp_obj.domain.min, hp_obj.domain.max, descr['n'])
                elif descr['type'] == 'interval_int':
                    hp_val = hp.IntInterval(descr['min'], descr['max'])
                    hp_obj = hp.HParam(key, hp_val)
                    self._parameter_list[key] = tf.range(hp_obj.domain.min, hp_obj.domain.max, descr['step'])

                self._hparams.append(hp_obj)
            self._combinations = [dict(zip(self._parameter_list, x)) for x in itertools.product(*self._parameter_list.values())]
            
    def _get_driver_dir(self):
        return "tensorboard"

class WandBLogger(TensorboardLogger):

    def __init__(self, base_dir, parameters, tuning):
        log_dir = base_dir + parameters['log_dir']

        wandb.tensorboard.patch(root_logdir=log_dir + "/" + super()._get_driver_dir(),tensorboardX=False)
        wandb.init(sync_tensorboard=True, project="rl-flatland", entity="fltlnd", dir=log_dir)
        super().__init__(base_dir, parameters, tuning=tuning)

    #     if self._hp_tuning:
    #         sweep_config = {
    #             'name': "prova1",
    #             'method': "random",
    #             'parameters': {
    #                 "batch_size": {
    #                     "values": [16, 32]
    #                 },
    #                 "learning_rate": {
    #                     "values": [0.5e-4, 0.5e-3]
    #                 }
    #             }
    #         }
    #         sweep_id = wandb.sweep(sweep_config)
    #         self._sweep = wandb.controller(sweep_id)

    # def get_run_params(self):
    #     if self._hp_tuning:
    #         for c in self._combinations:
    #             self._sweep.schedule(c)
    #             self._sweep.print_status()
    #             yield c
    #     else:
    #         yield [{}]
         
    def episode_start(self, run_params):
        wandb.config.update(run_params)
        return super().episode_start(run_params)