# -*- coding: utf-8 -*-

import os
import json
from json import encoder

import numpy as np
from sklearn_porter.estimator.classifier.Classifier import Classifier


class BernoulliNB(Classifier):
    """
    See also
    --------
    sklearn.naive_bayes.BernoulliNB

    http://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.BernoulliNB.html
    """

    SUPPORTED_METHODS = ['predict']

    # @formatter:off
    TEMPLATES = {
        'java': {
            'type':     '{0}',
            'arr':      '{{{0}}}',
            'arr[]':    '{type}[] {name} = {{{values}}};',
            'arr[][]':  '{type}[][] {name} = {{{values}}};',
            'indent':   '    ',
        },
        'js': {
            'type':     '{0}',
            'arr':      '[{0}]',
            'arr[]':    'var {name} = [{values}];',
            'arr[][]':  'var {name} = [{values}];',
            'indent':   '    ',
        }
    }
    # @formatter:on

    def __init__(self, estimator, target_language='java',
                 target_method='predict', **kwargs):
        """
        Port a trained estimator to the syntax of a chosen programming language.

        Parameters
        ----------
        :param estimator : AdaBoostClassifier
            An instance of a trained BernoulliNB estimator.
        :param target_language : string
            The target programming language.
        :param target_method : string
            The target method of the estimator.
        """
        super(BernoulliNB, self).__init__(
            estimator, target_language=target_language,
            target_method=target_method, **kwargs)
        self.estimator = estimator

    def export(self, class_name, method_name,
               export_data=False, export_dir='.', export_filename='data.json',
               **kwargs):
        """
        Port a trained estimator to the syntax of a chosen programming language.

        Parameters
        ----------
        :param class_name : string
            The name of the class in the returned result.
        :param method_name : string
            The name of the method in the returned result.
        :param export_data : bool
            Whether the model data should be saved or not.
        :param export_dir : string
            The directory where the model data should be saved.
        :param export_filename : string
            The filename of the exported model data.

        Returns
        -------
        :return : string
            The transpiled algorithm with the defined placeholders.
        """
        # Arguments:
        self.class_name = class_name
        self.method_name = method_name

        # Estimator:
        est = self.estimator

        self.n_classes = len(est.classes_)
        self.n_features = len(est.feature_log_prob_[0])

        temp_type = self.temp('type')
        temp_arr = self.temp('arr')
        temp_arr_ = self.temp('arr[]')
        temp_arr__ = self.temp('arr[][]')

        # Create class prior probabilities:
        priors = [self.temp('type').format(self.repr(p)) for p in
                  est.class_log_prior_]
        priors = ', '.join(priors)
        self.priors = temp_arr_.format(type='double', name='priors',
                                       values=priors)

        # Create negative probabilities:
        neg_prob = np.log(1 - np.exp(est.feature_log_prob_))
        probs = []
        for prob in neg_prob:
            tmp = [temp_type.format(self.repr(p)) for p in prob]
            tmp = temp_arr.format(', '.join(tmp))
            probs.append(tmp)
        probs = ', '.join(probs)
        self.neg_probs = temp_arr__.format(type='double', name='negProbs',
                                           values=probs)

        delta_probs = (est.feature_log_prob_ - neg_prob).T
        probs = []
        for prob in delta_probs:
            tmp = [temp_type.format(self.repr(p)) for p in prob]
            tmp = temp_arr.format(', '.join(tmp))
            probs.append(tmp)
        probs = ', '.join(probs)
        self.del_probs = temp_arr__.format(type='double', name='delProbs',
                                           values=probs)

        if self.target_method == 'predict':
            # Exported:
            if export_data and os.path.isdir(export_dir):
                self.export_data(export_dir, export_filename)
                return self.predict('exported')
            # Separated:
            return self.predict('separated')

    def predict(self, temp_type):
        """
        Transpile the predict method.

        Parameters
        ----------
        :param temp_type : string
            The kind of export type (embedded, separated, exported).

        Returns
        -------
        :return : string
            The transpiled predict method as string.
        """
        # Exported:
        if temp_type == 'exported':
            temp = self.temp('exported.class')
            return temp.format(class_name=self.class_name,
                               method_name=self.method_name)

        # Separated
        method = self.create_method()
        return self.create_class(method)

    def export_data(self, directory, filename):
        """
        Save model data in a JSON file.

        Parameters
        ----------
        :param directory : string
            The directory.
        :param filename : string
            The filename.
        """
        neg_prob = np.log(1 - np.exp(self.estimator.feature_log_prob_))
        delta_probs = (self.estimator.feature_log_prob_ - neg_prob).T
        model_data = {
            'priors': self.estimator.class_log_prior_.tolist(),
            'negProbs': neg_prob.tolist(),
            'delProbs': delta_probs.tolist()
        }
        encoder.FLOAT_REPR = lambda o: self.repr(o)
        path = os.path.join(directory, filename)
        with open(path, 'w') as fp:
            json.dump(model_data, fp)

    def create_method(self):
        """
        Build the estimator method or function.

        Returns
        -------
        :return : string
            The built method as string.
        """
        n_indents = 1 if self.target_language in ['java', 'js'] else 0
        temp_method = self.temp('separated.method.predict', n_indents=n_indents,
                                skipping=True)
        return temp_method.format(**self.__dict__)

    def create_class(self, method):
        """
        Build the estimator class.

        Returns
        -------
        :return : string
            The built class as string.
        """
        self.__dict__.update(dict(method=method))
        temp_class = self.temp('separated.class')
        return temp_class.format(**self.__dict__)
