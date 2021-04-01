from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from mot.common.gaussian_density import GaussianDensity
from mot.common.state import Gaussian
from mot.measurement_models import MeasurementModel
from mot.motion_models import MotionModel
from mot.trackers.multiple_object_trackers.PMBM.common.track import (
    SingleTargetHypothesis,
    Track,
)


class Bernoulli:
    """Bernoulli component

    Parameters
    ----------
    state : Gaussian
        a struct contains parameters describing the object pdf
    r : scalar
        probability of existence
    """

    def __init__(self, state: Gaussian, existence_probability: float):
        self.state: Gaussian = state
        self.existence_probability: float = existence_probability

    def __repr__(self) -> str:
        return self.__class__.__name__ + (
            f"(r={self.existence_probability:.4f}, " f"state={self.state}, "
        )

    def predict(
        self,
        motion_model: MotionModel,
        survival_probability: float,
        density=GaussianDensity,
        dt: float = 1.0,
    ) -> None:
        """Performs prediciton step for a Bernoulli component"""

        # Probability of survival * Probability of existence
        next_existence_probability = survival_probability * self.existence_probability

        # Kalman prediction of the new state
        self.state = density.predict(self.state, motion_model, dt)

        predicted_bern = Bernoulli(next_state, next_existence_probability)
        return predicted_bern

    def undetected_update(self, detection_probability: float):
        """Calculates the likelihood of missed detection,
        and creates new local hypotheses due to missed detection.
        NOTE: from page 88 lecture 04

        Parameters
        ----------
        detection_probability : scalar
            object detection probability

        Returns
        -------
        Bern
            [description]

        likelihood_undetectd : scalar

        """

        missdetecion_probability = 1 - detection_probability
        # update probability of existence
        posterior_existence_probability = (self.existence_probability * (1 - detection_probability)) / (1 - self.existence_probability + self.existence_probability * (1 - detection_probability))

        # state remains the same
        posterior_bern = Bernoulli(
            initial_state=self.state,
            existence_probability=posterior_existence_probability,
        )

        likelihood_predicted = (
            1
            - self.existence_probability
            + self.existence_probability * missdetecion_probability
        )
        log_likelihood_predicted = np.log(likelihood_predicted)
        return posterior_bern, log_likelihood_predicted

    def detected_update_likelihood(
        self,
        measurements: np.ndarray,
        meas_model: MeasurementModel,
        detection_probability: float,
        density=GaussianDensity,
    ) -> np.ndarray:
        """Calculates the predicted likelihood for a given local hypothesis.
        NOTE page 86 lecture 04
        """

        assert isinstance(meas_model, MeasurementModel)
        log_likelihood_detected = (
            density.predict_loglikelihood(self.state, measurements, meas_model)
            + np.log(detection_probability)
            + np.log(self.existence_probability)
        )
        return log_likelihood_detected

    @staticmethod
    def detected_update_state(
        bern, z: np.ndarray, meas_model: MeasurementModel, density=GaussianDensity
    ):
        """Creates the new local hypothesis due to measurement update.
        NOTE: page 85 lecture 04

        """
        assert isinstance(meas_model, MeasurementModel)

        updated_density = density.update(bern.state, z, meas_model)
        update_bern = Bernoulli(state=updated_density, existence_probability=1.0)
        return update_bern
