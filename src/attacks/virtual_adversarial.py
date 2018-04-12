from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np

from src.attacks.attack import Attack


class VirtualAdversarialMethod(Attack):
    """
    This attack was originally proposed by Miyato et al. (2016) and was used for virtual adversarial training.
    Paper link: https://arxiv.org/abs/1507.00677
    """
    attack_params = ['eps', 'finite_diff', 'max_iter']

    def __init__(self, classifier, max_iter=1, finite_diff=1e-6, eps=.1):
        """
        Create a VirtualAdversarialMethod instance.

        :param classifier: A trained model.
        :type classifier: :class:`Classifier`
        :param eps: Attack step (max input variation).
        :type eps: `float`
        :param finite_diff: The finite difference parameter.
        :type finite_diff: `float`
        :param max_iter: The maximum number of iterations.
        :type max_iter: `int`
        """
        super(VirtualAdversarialMethod, self).__init__(classifier)

        kwargs = {'finite_diff': finite_diff, 'eps': eps, 'max_iter': max_iter}
        self.set_params(**kwargs)

    def generate(self, x, **kwargs):
        """
        Generate adversarial samples and return them in an array.

        :param x: An array with the original inputs to be attacked.
        :type x: `np.ndarray`
        :param eps: Attack step (max input variation).
        :type eps: `float`
        :param finite_diff: The finite difference parameter.
        :type finite_diff: `float`
        :param max_iter: The maximum number of iterations.
        :type max_iter: `int`
        :return: An array holding the adversarial examples.
        :rtype: `np.ndarray`
        """
        # TODO Consider computing attack for a batch of samples at a time (no for loop)
        # Parse and save attack-specific parameters
        assert self.set_params(**kwargs)
        clip_min, clip_max = self.classifier.clip_values

        x_adv = np.copy(x)
        dims = list(x.shape[1:])
        preds = self.classifier.predict(x_adv, logits=False)

        for ind, val in enumerate(x_adv):
            d = np.random.randn(*dims)
            e = np.random.randn(*dims)
            for _ in range(self.max_iter):
                d = self.finite_diff * self._normalize(d)
                e = self.finite_diff * self._normalize(e)
                preds_new = self.classifier.predict(np.stack((val + d, val + e)))

                # Compute KL divergence between logits
                from scipy.stats import entropy
                kl_div1 = entropy(preds[ind], preds_new[0])
                kl_div2 = entropy(preds[ind], preds_new[1])
                d = (kl_div1 - kl_div2) / np.abs(d - e)

            # Apply perturbation and clip
            val = np.clip(val + self.eps * self._normalize(d), clip_min, clip_max)
            x_adv[ind] = val

        return x_adv

    @staticmethod
    def _normalize(x):
        """
        Apply L_2 batch normalization on `x`.

        :param x: The input array to normalize.
        :type x: `np.ndarray`
        :return: The normalized version of `x`.
        :rtype: `np.ndarray`
        """
        tol = 1e-12
        dims = x.shape

        x = x.flatten()
        x /= np.max(np.abs(x)) + tol
        inverse = (np.sum(x**2) + np.sqrt(tol)) ** -.5
        x = x * inverse
        x = np.reshape(x, dims)

        return x

    def set_params(self, **kwargs):
        """
        Take in a dictionary of parameters and applies attack-specific checks before saving them as attributes.

        :param eps: Attack step (max input variation).
        :type eps: `float`
        :param finite_diff: The finite difference parameter.
        :type finite_diff: `float`
        :param max_iter: The maximum number of iterations.
        :type max_iter: `int`
        """
        # Save attack-specific parameters
        super(VirtualAdversarialMethod, self).set_params(**kwargs)

        return True
