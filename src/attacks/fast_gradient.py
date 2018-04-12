from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from src.attacks.attack import Attack


class FastGradientMethod(Attack):
    """
    This attack was originally implemented by Goodfellow et al. (2015) with the infinity norm (and is known as the "Fast
    Gradient Sign Method"). This implementation extends the attack to other norms, and is therefore called the Fast
    Gradient Method. Paper link: https://arxiv.org/abs/1412.6572
    """
    attack_params = ['norm', 'eps', 'targeted']

    def __init__(self, classifier, norm=np.inf, eps=.3, targeted=False):
        """
        Create a FastGradientMethod instance.

        :param classifier: A trained model.
        :type classifier: :class:`Classifier`
        :param norm: Order of the norm. Possible values: np.inf, 1 or 2.
        :type norm: `int`
        :param eps: Attack step size (input variation)
        :type eps: `float`
        :param targeted: Should the attack target one specific class
        :type targeted: `bool`
        """
        super(FastGradientMethod, self).__init__(classifier)

        kwargs = {'norm': norm, 'eps': eps, 'targeted': targeted}
        self.set_params(**kwargs)

    def _minimal_perturbation(self, x, y, eps_step=0.1, eps_max=1., **kwargs):
        """Iteratively compute the minimal perturbation necessary to make the class prediction change. Stop when the
        first adversarial example was found.

        :param x: An array with the original inputs
        :type x: `np.ndarray`
        :param y:
        :type y:
        :param eps_step: The increase in the perturbation for each iteration
        :type eps_step: `float`
        :param eps_max: The maximum accepted perturbation
        :type eps_max: `float`
        :param kwargs: Other parameters to send to `generate_graph`
        :type kwargs: `dict`
        :return: An array holding the adversarial examples
        :rtype: `np.ndarray`
        """
        self.set_params(**kwargs)
        adv_x = x.copy()

        # Get current predictions
        active_indices = np.arange(len(adv_x))
        current_eps = eps_step

        while len(active_indices) != 0 and current_eps <= eps_max:
            # Adversarial crafting
            current_x = self._compute(x[active_indices], y[active_indices], current_eps)
            adv_preds = self.classifier.predict(adv_x)

            # Update
            adv_x[active_indices] = current_x
            active_indices = np.where(np.argmax(y[active_indices], axis=1) == np.argmax(adv_preds, axis=1))
            current_eps += eps_step

        return adv_x

    def generate(self, x, **kwargs):
        """Generate adversarial samples and return them in an array.

        :param x: An array with the original inputs.
        :type x: `np.ndarray`
        :param eps: Attack step size (input variation)
        :type eps: `float`
        :param ord: Order of the norm (mimics Numpy). Possible values: np.inf, 1 or 2.
        :type ord: `int`
        :param y: The labels for the data `x`. Only provide this parameter if you'd like to use true
                  labels when crafting adversarial samples. Otherwise, model predictions are used as labels to avoid the
                  "label leaking" effect (explained in this paper: https://arxiv.org/abs/1611.01236). Default is `None`.
                  Labels should be one-hot-encoded.
        :type y: `np.ndarray`
        :param minimal: `True` if only the minimal perturbation should be computed. In that case, use `eps_step` for the
                        step size and `eps_max` for the total allowed perturbation.
        :type minimal: `bool`
        :return: An array holding the adversarial examples.
        :rtype: `np.ndarray`
        """
        self.set_params(**kwargs)

        if 'y' not in kwargs or kwargs[str('y')] is None:
            # Use model predictions as correct outputs
            y = self.classifier.predict(x)
        else:
            y = kwargs[str('y')]
        y = y / np.sum(y, axis=1, keepdims=True)

        # Return adversarial examples computed with minimal perturbation if option is active
        if 'minimal' in kwargs and kwargs[str('minimal')]:
            return self._minimal_perturbation(x, y, **kwargs)

        return self._compute(x, y, self.eps)

    def set_params(self, **kwargs):
        """
        Take in a dictionary of parameters and applies attack-specific checks before saving them as attributes.

        :param norm: Order of the norm. Possible values: np.inf, 1 or 2.
        :type norm: `int` or `float`
        :param eps: Attack step size (input variation)
        :type eps: `float`
        :param targeted: Should the attack target one specific class
        :type targeted: `bool`
        """
        # Save attack-specific parameters
        super(FastGradientMethod, self).set_params(**kwargs)

        # Check if order of the norm is acceptable given current implementation
        if self.norm not in [np.inf, int(1), int(2)]:
            raise ValueError('Norm order must be either `np.inf`, 1, or 2.')

        clip_min, clip_max = self.classifier.clip_values
        if self.eps <= clip_min or self.eps > clip_max:
            raise ValueError('The amount of perturbation has to be in the data range.')

        return True

    def _compute(self, x, y, eps):
        # Get gradient wrt loss; invert it if attack is targeted
        grad = self.classifier.loss_gradient(x, y) * (1 - 2 * int(self.targeted))

        # Apply norm bound
        if self.norm == np.inf:
            grad = np.sign(grad)
        elif self.norm == 1:
            ind = tuple(range(1, len(x.shape)))
            grad = grad / np.sum(np.abs(grad), axis=ind, keepdims=True)
        elif self.norm == 2:
            ind = tuple(range(1, len(x.shape)))
            grad = grad / np.sqrt(np.sum(np.square(grad), axis=ind, keepdims=True))
        assert x.shape == grad.shape

        # Apply perturbation and clip
        clip_min, clip_max = self.classifier.clip_values
        x_adv = x + eps * grad
        x_adv = np.clip(x_adv, clip_min, clip_max)

        return x_adv
