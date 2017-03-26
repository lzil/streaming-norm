import collections
import math

import numpy as np
import tensorflow as tf

import streaming

if tf.__version__ == '1.0.0':
    rnn_cell = tf.contrib.rnn
else:
    rnn_cell = tf.nn.rnn_cell


def sn(input, s, b, epsilon=1e-5, max=1000, name='snorm'):
    """ Streaming normalizes a 2D tensor along its 1st axis, which corresponds to batch """
    m, v = tf.nn.moments(input, [0], keep_dims=True)
    v_sqrt = tf.sqrt(v + epsilon)
    m_stream = streaming.stream(m, name + 'sm')
    v_sqrt_stream = streaming.stream(v_sqrt, name + 'sv')
    normalised_input = (input - m_stream) / v_sqrt_stream
    return normalised_input * s + b


class SNGRUCell(rnn_cell.RNNCell):
    def __init__(self, num_units, input_size=None, activation=tf.tanh):
        if input_size is not None:
            print("%s: The input_size parameter is deprecated." % self)
        self._num_units = num_units
        self._activation = activation

    @property
    def state_size(self):
        return self._num_units

    @property
    def output_size(self):
        return self._num_units

    def __call__(self, inputs, state, scope=None):
        """Gated recurrent unit (GRU) with nunits cells."""
        dim = self._num_units
        with tf.variable_scope(scope or type(self).__name__):  # "GRUCell"
            with tf.variable_scope("Gates"):  # Reset gate and update gate.
                # We start with bias of 1.0 to not reset and not update.
                with tf.variable_scope("Layer_Parameters"):

                    s1 = tf.get_variable("s1", initializer=tf.ones(
                        [2 * dim]), dtype=tf.float32)
                    s2 = tf.get_variable("s2", initializer=tf.ones(
                        [2 * dim]), dtype=tf.float32)
                    s3 = tf.get_variable(
                        "s3", initializer=tf.ones([dim]), dtype=tf.float32)
                    s4 = tf.get_variable(
                        "s4", initializer=tf.ones([dim]), dtype=tf.float32)
                    b1 = tf.get_variable("b1", initializer=tf.zeros(
                        [2 * dim]), dtype=tf.float32)
                    b2 = tf.get_variable("b2", initializer=tf.zeros(
                        [2 * dim]), dtype=tf.float32)
                    b3 = tf.get_variable(
                        "b3", initializer=tf.zeros([dim]), dtype=tf.float32)
                    b4 = tf.get_variable(
                        "b4", initializer=tf.zeros([dim]), dtype=tf.float32)

                input_below_ = rnn_cell._linear([inputs],
                                                2 * self._num_units, False, scope="out_1")
                input_below_ = sn(input_below_, s1, b1, name='g_in')
                state_below_ = rnn_cell._linear([state],
                                                2 * self._num_units, False, scope="out_2")
                state_below_ = sn(state_below_, s2, b2, name='g_st')
                out = tf.add(input_below_, state_below_)
                r, u = tf.split(1, 2, out)
                r, u = tf.sigmoid(r), tf.sigmoid(u)

            with tf.variable_scope("Candidate"):
                input_below_x = rnn_cell._linear([inputs],
                                                 self._num_units, False, scope="out_3")
                input_below_x = sn(input_below_x, s3, b3, name='c_in')
                state_below_x = rnn_cell._linear([state],
                                                 self._num_units, False, scope="out_4")
                state_below_x = sn(state_below_x, s4, b4, name='c_st')
                c_pre = tf.add(input_below_x, r * state_below_x)
                c = self._activation(c_pre)
            new_h = u * state + (1 - u) * c
        return new_h, new_h


def ln(input, s, b, epsilon=1e-5, max=1000):
    """ Layer normalizes a 2D tensor along its second axis, which corresponds to batch """
    m, v = tf.nn.moments(input, [1], keep_dims=True)
    normalised_input = (input - m) / tf.sqrt(v + epsilon)
    return normalised_input * s + b


class LNGRUCell(rnn_cell.RNNCell):
    """Gated Recurrent Unit cell (cf. http://arxiv.org/abs/1406.1078)."""
    def __init__(self, num_units, input_size=None, activation=tf.tanh):
        if input_size is not None:
            print("%s: The input_size parameter is deprecated." % self)
        self._num_units = num_units
        self._activation = activation

    @property
    def state_size(self):
        return self._num_units

    @property
    def output_size(self):
        return self._num_units

    def __call__(self, inputs, state, scope=None):
        """Gated recurrent unit (GRU) with nunits cells."""
        dim = self._num_units
        with tf.variable_scope(scope or type(self).__name__):  # "GRUCell"
            with tf.variable_scope("Gates"):  # Reset gate and update gate.
                # We start with bias of 1.0 to not reset and not update.
                with tf.variable_scope("Layer_Parameters"):

                    s1 = tf.get_variable("s1", initializer=tf.ones(
                        [2 * dim]), dtype=tf.float32)
                    s2 = tf.get_variable("s2", initializer=tf.ones(
                        [2 * dim]), dtype=tf.float32)
                    s3 = tf.get_variable(
                        "s3", initializer=tf.ones([dim]), dtype=tf.float32)
                    s4 = tf.get_variable(
                        "s4", initializer=tf.ones([dim]), dtype=tf.float32)
                    b1 = tf.get_variable("b1", initializer=tf.zeros(
                        [2 * dim]), dtype=tf.float32)
                    b2 = tf.get_variable("b2", initializer=tf.zeros(
                        [2 * dim]), dtype=tf.float32)
                    b3 = tf.get_variable(
                        "b3", initializer=tf.zeros([dim]), dtype=tf.float32)
                    b4 = tf.get_variable(
                        "b4", initializer=tf.zeros([dim]), dtype=tf.float32)

                    # Code below initialized for all cells
                    # s1 = tf.Variable(tf.ones([2 * dim]), name="s1")
                    # s2 = tf.Variable(tf.ones([2 * dim]), name="s2")
                    # s3 = tf.Variable(tf.ones([dim]), name="s3")
                    # s4 = tf.Variable(tf.ones([dim]), name="s4")
                    # b1 = tf.Variable(tf.zeros([2 * dim]), name="b1")
                    # b2 = tf.Variable(tf.zeros([2 * dim]), name="b2")
                    # b3 = tf.Variable(tf.zeros([dim]), name="b3")
                    # b4 = tf.Variable(tf.zeros([dim]), name="b4")

                input_below_ = rnn_cell._linear([inputs],
                                                2 * self._num_units, False, scope="out_1")
                input_below_ = ln(input_below_, s1, b1)

                state_below_ = rnn_cell._linear([state],
                                                2 * self._num_units, False, scope="out_2")
                state_below_ = ln(state_below_, s2, b2)
                out = tf.add(input_below_, state_below_)
                r, u = tf.split(1, 2, out)
                r, u = tf.sigmoid(r), tf.sigmoid(u)

            with tf.variable_scope("Candidate"):
                input_below_x = rnn_cell._linear([inputs],
                                                 self._num_units, False, scope="out_3")
                input_below_x = ln(input_below_x, s3, b3)
                state_below_x = rnn_cell._linear([state],
                                                 self._num_units, False, scope="out_4")
                state_below_x = ln(state_below_x, s4, b4)
                c_pre = tf.add(input_below_x, r * state_below_x)
                c = self._activation(c_pre)
            new_h = u * state + (1 - u) * c
        return new_h, new_h

_LNLSTMStateTuple = collections.namedtuple("LNLSTMStateTuple", ("c", "h"))


class LSTMStateTuple(_LNLSTMStateTuple):
    """Tuple used by LSTM Cells for `state_size`, `zero_state`, and output state.
    Stores two elements: `(c, h)`, in that order.
    Only used when `state_is_tuple=True`.
    """
    __slots__ = ()


class LNBasicLSTMCell(rnn_cell.RNNCell):
    """Basic LSTM recurrent network cell.
    The implementation is based on: http://arxiv.org/abs/1409.2329.
    We add forget_bias (default: 1) to the biases of the forget gate in order to
    reduce the scale of forgetting in the beginning of the training.
    It does not allow cell clipping, a projection layer, and does not
    use peep-hole connections: it is the basic baseline.
    For advanced models, please use the full LSTMCell that follows.
    """

    def __init__(self, num_units, forget_bias=1.0, input_size=None,
        state_is_tuple=False, activation=tf.tanh):
        """Initialize the basic LSTM cell.
        Args:
          num_units: int, The number of units in the LSTM cell.
          forget_bias: float, The bias added to forget gates (see above).
          input_size: Deprecated and unused.
          state_is_tuple: If True, accepted and returned states are 2-tuples of
            the `c_state` and `m_state`.  By default (False), they are concatenated
            along the column axis.  This default behavior will soon be deprecated.
          activation: Activation function of the inner states.
        """
        if not state_is_tuple:
            print("%s: Using a concatenated state is slower and will soon be "
                  "deprecated.  Use state_is_tuple=True.", self)
        if input_size is not None:
            print("%s: The input_size parameter is deprecated.", self)
        self._num_units = num_units
        self._forget_bias = forget_bias
        self._state_is_tuple = state_is_tuple
        self._activation = activation

    @property
    def state_size(self):
        return (LSTMStateTuple(self._num_units, self._num_units)
                if self._state_is_tuple else 2 * self._num_units)

    @property
    def output_size(self):
        return self._num_units

    def __call__(self, inputs, state, scope=None):
        """Long short-term memory cell (LSTM)."""
        with tf.variable_scope(scope or type(self).__name__):  # "BasicLSTMCell"
            # Parameters of gates are concatenated into one multiply for
            # efficiency.
            if self._state_is_tuple:
                c, h = state
            else:
                c, h = tf.split(1, 2, state)

            s1 = tf.get_variable("s1", initializer=tf.ones(
                [4 * self._num_units]), dtype=tf.float32)
            s2 = tf.get_variable("s2", initializer=tf.ones(
                [4 * self._num_units]), dtype=tf.float32)
            s3 = tf.get_variable("s3", initializer=tf.ones(
                [self._num_units]), dtype=tf.float32)

            b1 = tf.get_variable("b1", initializer=tf.zeros(
                [4 * self._num_units]), dtype=tf.float32)
            b2 = tf.get_variable("b2", initializer=tf.zeros(
                [4 * self._num_units]), dtype=tf.float32)
            b3 = tf.get_variable("b3", initializer=tf.zeros(
                [self._num_units]), dtype=tf.float32)

            # s1 = tf.Variable(tf.ones([4 * self._num_units]), name="s1")
            # s2 = tf.Variable(tf.ones([4 * self._num_units]), name="s2")
            # s3 = tf.Variable(tf.ones([self._num_units]), name="s3")
            #
            # b1 = tf.Variable(tf.zeros([4 * self._num_units]), name="b1")
            # b2 = tf.Variable(tf.zeros([4 * self._num_units]), name="b2")
            # b3 = tf.Variable(tf.zeros([self._num_units]), name="b3")

            input_below_ = rnn_cell._linear([inputs],
                                            4 * self._num_units, False, scope="out_1")
            input_below_ = ln(input_below_, s1, b1)
            state_below_ = rnn_cell._linear([h],
                                            4 * self._num_units, False, scope="out_2")
            state_below_ = ln(state_below_, s2, b2)
            lstm_matrix = tf.add(input_below_, state_below_)

            i, j, f, o = tf.split(1, 4, lstm_matrix)

            new_c = (c * tf.sigmoid(f) + tf.sigmoid(i) *
                     self._activation(j))

            # Currently normalizing c causes lot of nan's in the model, thus commenting it out for now.
            # new_c_ = ln(new_c, s3, b3)
            new_c_ = new_c
            new_h = self._activation(new_c_) * tf.sigmoid(o)

            if self._state_is_tuple:
                new_state = LSTMStateTuple(new_c, new_h)
            else:
                new_state = tf.concat(1, [new_c, new_h])
            return new_h, new_state


class HyperLnLSTMCell(rnn_cell.RNNCell):
    """Basic LSTM recurrent network cell.
    The implementation is based on: http://arxiv.org/abs/1409.2329.
    We add forget_bias (default: 1) to the biases of the forget gate in order to
    reduce the scale of forgetting in the beginning of the training.
    It does not allow cell clipping, a projection layer, and does not
    use peep-hole connections: it is the basic baseline.
    For advanced models, please use the full LSTMCell that follows.
    """

    def __init__(self, num_units, forget_bias=1.0, input_size=None, 
        state_is_tuple=False, activation=tf.tanh, hyper_num_units=128, hyper_embedding_size=32, is_layer_norm=True):
        """Initialize the basic LSTM cell.
        Args:
          num_units: int, The number of units in the LSTM cell.
          hyper_num_units: int, The number of units in the HyperLSTM cell.
          forget_bias: float, The bias added to forget gates (see above).
          input_size: Deprecated and unused.
          state_is_tuple: If True, accepted and returned states are 2-tuples of
            the `c_state` and `m_state`.  By default (False), they are concatenated
            along the column axis.  This default behavior will soon be deprecated.
          activation: Activation function of the inner states.
        """
        if not state_is_tuple:
            print("%s: Using a concatenated state is slower and will soon be "
                  "deprecated.  Use state_is_tuple=True.", self)
        if input_size is not None:
            print("%s: The input_size parameter is deprecated.", self)
        self._num_units = num_units
        self._forget_bias = forget_bias
        self._state_is_tuple = state_is_tuple
        self._activation = activation
        self.hyper_num_units = hyper_num_units
        self.total_num_units = self._num_units + self.hyper_num_units
        self.hyper_cell = rnn_cell.BasicLSTMCell(hyper_num_units)
        self.hyper_embedding_size = hyper_embedding_size
        self.is_layer_norm = is_layer_norm

    @property
    def state_size(self):
        return 2 * self.total_num_units
        # return (LSTMStateTuple(self._num_units, self._num_units)
        #         if self._state_is_tuple else 2 * self._num_units)

    @property
    def output_size(self):
        return self._num_units

    def hyper_norm(self, layer, dimensions, scope="hyper"):
        with tf.variable_scope(scope):
            zw = rnn_cell._linear(self.hyper_output,
                                  self.hyper_embedding_size, False, scope=scope + "z")
            alpha = rnn_cell._linear(
                zw, dimensions, False, scope=scope + "alpha")
            result = tf.mul(alpha, layer)

            return result

    def __call__(self, inputs, state, scope=None):
        """Long short-term memory cell (LSTM) with hypernetworks and layer normalization."""
        with tf.variable_scope(scope or type(self).__name__):
            # Parameters of gates are concatenated into one multiply for
            # efficiency.
            total_h, total_c = tf.split(1, 2, state)
            h = total_h[:, 0:self._num_units]
            c = total_c[:, 0:self._num_units]

            self.hyper_state = tf.concat(
                1, [total_h[:, self._num_units:], total_c[:, self._num_units:]])
            hyper_input = tf.concat(1, [inputs, h])
            hyper_output, hyper_new_state = self.hyper_cell(
                hyper_input, self.hyper_state)
            self.hyper_output = hyper_output
            self.hyper_state = hyper_new_state

            input_below_ = rnn_cell._linear([inputs],
                                            4 * self._num_units, False, scope="out_1")
            input_below_ = self.hyper_norm(
                input_below_, 4 * self._num_units, scope="hyper_x")
            state_below_ = rnn_cell._linear([h],
                                            4 * self._num_units, False, scope="out_2")
            state_below_ = self.hyper_norm(
                state_below_, 4 * self._num_units, scope="hyper_h")

            if self.is_layer_norm:
                s1 = tf.get_variable("s1", initializer=tf.ones(
                    [4 * self._num_units]), dtype=tf.float32)
                s2 = tf.get_variable("s2", initializer=tf.ones(
                    [4 * self._num_units]), dtype=tf.float32)
                s3 = tf.get_variable("s3", initializer=tf.ones(
                    [self._num_units]), dtype=tf.float32)

                b1 = tf.get_variable("b1", initializer=tf.zeros(
                    [4 * self._num_units]), dtype=tf.float32)
                b2 = tf.get_variable("b2", initializer=tf.zeros(
                    [4 * self._num_units]), dtype=tf.float32)
                b3 = tf.get_variable("b3", initializer=tf.zeros(
                    [self._num_units]), dtype=tf.float32)

                input_below_ = ln(input_below_, s1, b1)

                state_below_ = ln(state_below_, s2, b2)

            lstm_matrix = tf.add(input_below_, state_below_)
            i, j, f, o = tf.split(1, 4, lstm_matrix)
            new_c = (c * tf.sigmoid(f) + tf.sigmoid(i) * self._activation(j))

            # Currently normalizing c causes lot of nan's in the model, thus commenting it out for now.
            # new_c_ = ln(new_c, s3, b3)
            new_c_ = new_c
            new_h = self._activation(new_c_) * tf.sigmoid(o)

            hyper_h, hyper_c = tf.split(1, 2, hyper_new_state)
            new_total_h = tf.concat(1, [new_h, hyper_h])
            new_total_c = tf.concat(1, [new_c, hyper_c])
            new_total_state = tf.concat(1, [new_total_h, new_total_c])
            return new_h, new_total_state


class LNLSTMCell(rnn_cell.RNNCell):
    """Long short-term memory unit (LSTM) recurrent network cell.
    The default non-peephole implementation is based on:
      http://deeplearning.cs.cmu.edu/pdfs/Hochreiter97_lstm.pdf
    S. Hochreiter and J. Schmidhuber.
    "Long Short-Term Memory". Neural Computation, 9(8):1735-1780, 1997.
    The peephole implementation is based on:
      https://research.google.com/pubs/archive/43905.pdf
    Hasim Sak, Andrew Senior, and Francoise Beaufays.
    "Long short-term memory recurrent neural network architectures for
     large scale acoustic modeling." INTERSPEECH, 2014.
    The class uses optional peep-hole connections, optional cell clipping, and
    an optional projection layer.
    """

    def __init__(self, num_units, input_size=None, initializer=None,
        num_proj=None, state_is_tuple=False, activation=tf.tanh):
        """Initialize the parameters for an LSTM cell.
        Args:
          num_units: int, The number of units in the LSTM cell
          input_size: Deprecated and unused.
          use_peepholes: bool, set True to enable diagonal/peephole connections.
          cell_clip: (optional) A float value, if provided the cell state is clipped
            by this value prior to the cell output activation.
          initializer: (optional) The initializer to use for the weight and
            projection matrices.
          num_proj: (optional) int, The output dimensionality for the projection
            matrices.  If None, no projection is performed.
          proj_clip: (optional) A float value.  If `num_proj > 0` and `proj_clip` is
          provided, then the projected values are clipped elementwise to within
          `[-proj_clip, proj_clip]`.
          num_unit_shards: How to split the weight matrix.  If >1, the weight
            matrix is stored across num_unit_shards.
          num_proj_shards: How to split the projection matrix.  If >1, the
            projection matrix is stored across num_proj_shards.
          forget_bias: Biases of the forget gate are initialized by default to 1
            in order to reduce the scale of forgetting at the beginning of
            the training.
          state_is_tuple: If True, accepted and returned states are 2-tuples of
            the `c_state` and `m_state`.  By default (False), they are concatenated
            along the column axis.  This default behavior will soon be deprecated.
          activation: Activation function of the inner states.
        """
        if not state_is_tuple:
            print(
                "%s: Using a concatenated state is slower and will soon be "
                "deprecated.  Use state_is_tuple=True." % self)
        if input_size is not None:
            print("%s: The input_size parameter is deprecated." % self)
        self._num_units = num_units
        self._initializer = initializer
        self._num_proj = num_proj
        self._state_is_tuple = state_is_tuple
        self._activation = activation

        if num_proj:
            self._state_size = (
                LSTMStateTuple(num_units, num_proj)
                if state_is_tuple else num_units + num_proj)
            self._output_size = num_proj
        else:
            self._state_size = (
                LSTMStateTuple(num_units, num_units)
                if state_is_tuple else 2 * num_units)
            self._output_size = num_units

    @property
    def state_size(self):
        return self._state_size

    @property
    def output_size(self):
        return self._output_size

    def __call__(self, inputs, state, scope=None):
        """Run one step of LSTM.
        Args:
          inputs: input Tensor, 2D, batch x num_units.
          state: if `state_is_tuple` is False, this must be a state Tensor,
            `2-D, batch x state_size`.  If `state_is_tuple` is True, this must be a
            tuple of state Tensors, both `2-D`, with column sizes `c_state` and
            `m_state`.
          scope: VariableScope for the created subgraph; defaults to "LSTMCell".
        Returns:
          A tuple containing:
          - A `2-D, [batch x output_dim]`, Tensor representing the output of the
            LSTM after reading `inputs` when previous state was `state`.
            Here output_dim is:
               num_proj if num_proj was set,
               num_units otherwise.
          - Tensor(s) representing the new state of LSTM after reading `inputs` when
            the previous state was `state`.  Same type and shape(s) as `state`.
        Raises:
          ValueError: If input size cannot be inferred from inputs via
            static shape inference.
        """
        num_proj = self._num_units if self._num_proj is None else self._num_proj

        if self._state_is_tuple:
            (c_prev, m_prev) = state
        else:
            c_prev = tf.slice(state, [0, 0], [-1, self._num_units])
            m_prev = tf.slice(
                state, [0, self._num_units], [-1, num_proj])

        input_size = inputs.get_shape().with_rank(2)[1]
        if input_size.value is None:
            raise ValueError(
                "Could not infer input size from inputs.get_shape()[-1]")
        with tf.variable_scope(scope or type(self).__name__,
                               initializer=self._initializer):  # "LSTMCell"

            s1 = tf.get_variable("s1", initializer=tf.ones(
                [4 * self._num_units]), dtype=tf.float32)
            s2 = tf.get_variable("s2", initializer=tf.ones(
                [4 * self._num_units]), dtype=tf.float32)
            s3 = tf.get_variable("s3", initializer=tf.ones(
                [self._num_units]), dtype=tf.float32)

            b1 = tf.get_variable("b1", initializer=tf.zeros(
                [4 * self._num_units]), dtype=tf.float32)
            b2 = tf.get_variable("b2", initializer=tf.zeros(
                [4 * self._num_units]), dtype=tf.float32)
            b3 = tf.get_variable("b3", initializer=tf.zeros(
                [self._num_units]), dtype=tf.float32)

            # s1 = tf.Variable(tf.ones([4 * self._num_units]), name="s1")
            # s2 = tf.Variable(tf.ones([4 * self._num_units]), name="s2")
            # s3 = tf.Variable(tf.ones([self._num_units]), name="s3")
            #
            # b1 = tf.Variable(tf.zeros([4 * self._num_units]), name="b1")
            # b2 = tf.Variable(tf.zeros([4 * self._num_units]), name="b2")
            # b3 = tf.Variable(tf.zeros([self._num_units]), name="b3")

            input_below_ = rnn_cell._linear([inputs],
                                            4 * self._num_units, False, scope="out_1")
            input_below_ = ln(input_below_, s1, b1)
            state_below_ = rnn_cell._linear([m_prev],
                                            4 * self._num_units, False, scope="out_2")
            state_below_ = ln(state_below_, s2, b2)
            lstm_matrix = tf.add(input_below_, state_below_)

            i, j, f, o = tf.split(1, 4, lstm_matrix)

            c = (tf.sigmoid(f) * c_prev + tf.sigmoid(i) *
                 self._activation(j))

        # Currently normalizing c causes lot of nan's in the model, thus commenting it out for now.
           # c_ = ln(c, s3, b3)
            c_ = c
            m = tf.sigmoid(o) * self._activation(c_)

        new_state = (LSTMStateTuple(c, m) if self._state_is_tuple
                     else tf.concat(1, [c, m]))
        return m, new_state
