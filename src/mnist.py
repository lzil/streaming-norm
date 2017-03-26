import argparse
import tensorflow as tf
import numpy as np

from layers import *
import streaming

if tf.__version__ == '1.0.0'
    rnn_cell = tf.contrib.rnn
else:
    rnn_cell = tf.nn.rnn_cell

# Import MINST data
from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets("../data/", one_hot=True)


parser = argparse.ArgumentParser(description='Runs instance(s) of an RNN.')
parser.add_argument('--learning_rate', help='learning rate', type=float, default=0.001)
parser.add_argument('--iterations', help='number of iterations', type=int, default=100000)
parser.add_argument('--batch_size', help='batch size', type=int, default=128)
parser.add_argument('--display_step', help='# training steps per checkpoint', type=int, default=10)
parser.add_argument('--hidden', help='# hidden units', type=int, default=50)
parser.add_argument('--classes', help='# classes', type=int, default=10)
parser.add_argument('--layers', help='# layers', type=int, default=1)
parser.add_argument('--dau', help='batches per update for use in decoupled accumulation and update', type=int, default=1)
parser.add_argument('--cell_type', help='type of RNN', choices=['SNGRU', 'LSTM', 'GRU', 'BasicRNN', 'LNGRU', 'LNLSTM', 'HyperLnLSTMCell'], default='SNGRU')
parser.add_argument('--hyper_layer_norm', help='for HyperLnLSTMCell use only', action='store_true')
parser.add_argument('--summaries_dir', help='directory for summary', default='./log/')
args = parser.parse_args()

'''
To classify images using a reccurent neural network, we consider every image
row as a sequence of pixels. Because MNIST image shape is 28*28px, we will then
handle 28 sequences of 28 steps for every sample.
'''

tensorboard = False

# Parameters
learning_rate = args.learning_rate
training_iters = args.iterations
batch_size = args.batch_size
display_step = args.display_step

# Network Parameters
n_input = 28  # MNIST data input (img shape: 28*28)
n_steps = 28  # timesteps
n_hidden = args.hidden  # hidden layer num of features
n_classes = args.classes  # MNIST total classes (0-9 digits)

n_dau = args.dau

# alpha_global = [.7,.3]
# beta_global = [.7,.3,0]
# kappa_global = alpha_global * 2

print 'Learning rate: ' + str(learning_rate)
print 'Batch size: ' + str(batch_size)
print 'Hidden units: ' + str(n_hidden)
print 'DAU: ' + str(n_dau)
print 'Cell type: ' + str(args.cell_type)

# print 'alpha, beta, kappa: '
# print alpha_global
# print beta_global
# print kappa_global

streaming_norm_training_mode_global_flag = False

def train():
    global streaming_norm_training_mode_global_flag
    # global alpha_global
    # global beta_global
    # global kappa_global
    sess = tf.InteractiveSession()

    with tf.name_scope('input'):
        x = tf.placeholder(tf.float32, [None, n_steps, n_input], name='x-input')
        y = tf.placeholder(tf.float32, [None, n_classes], name='y-input')

    weights = {
        'out': tf.get_variable('weights', shape=[n_hidden, n_classes], initializer=tf.random_normal_initializer())
    }
    biases = {
        'out': tf.get_variable('biases', shape=[n_classes], initializer=tf.random_normal_initializer())
    }

    def RNN(x, weights, biases, type, hyper_layer_norm, scope=None):

        # Prepare data shape to match `rnn` function requirements
        # Current data input shape: (batch_size, n_steps, n_input)
        # Required shape: 'n_steps' tensors list of shape (batch_size, n_input)

        # Permuting batch_size and n_steps
        x = tf.transpose(x, [1, 0, 2])
        # Reshaping to (n_steps*batch_size, n_input)
        x = tf.reshape(x, [-1, n_input])
        # Split to get a list of 'n_steps' tensors of shape (batch_size, n_input)
        if tf.__version__ == '1.0.0':
            x = tf.split(x, n_steps, 0)
        else:
            x = tf.split(0, n_steps, x)

        # Define a lstm cell with tensorflow
        cell_class_map = {
            "LSTM": rnn_cell.BasicLSTMCell(n_hidden),
            "GRU": rnn_cell.GRUCell(n_hidden),
            "BasicRNN": rnn_cell.BasicRNNCell(n_hidden),
            "LNGRU": LNGRUCell(n_hidden),
            "SNGRU": SNGRUCell(n_hidden),
            "LNLSTM": LNBasicLSTMCell(n_hidden),
            'HyperLnLSTMCell': HyperLnLSTMCell(n_hidden, is_layer_norm=hyper_layer_norm)
        }

        lstm_cell = cell_class_map.get(type)
        cell = rnn_cell.MultiRNNCell([lstm_cell] * args.layers, state_is_tuple=True)
        print "Using %s model" % type
        # Get lstm cell output
        if tf.__version__ == '1.0.0':
            outputs, states = rnn_cell.static_rnn(cell, x, dtype=tf.float32, scope=scope)
        else:
            outputs, states = tf.nn.rnn(cell, x, dtype=tf.float32, scope=scope)

        # Linear activation, using rnn inner loop last output
        return tf.matmul(outputs[-1], weights['out']) + biases['out']

    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)

    pred = RNN(x, weights, biases, args.cell_type, args.hyper_layer_norm)
    # Define loss and optimizer
    # print pred
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(pred, y))
    grads = optimizer.compute_gradients(cost)

    grad_placeholder = [(tf.placeholder("float", shape=grad[0].get_shape()), grad[1]) for grad in grads]

    apply_grads = optimizer.apply_gradients(grad_placeholder)

    correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    if tensorboard:
        tf.summary.scalar('Accuracy', accuracy)
        tf.summary.scalar('Cost', cost)

        merged = tf.summary.merge_all()
        train_writer = tf.summary.FileWriter(args.summaries_dir + "train/", sess.graph)
        test_writer = tf.summary.FileWriter(args.summaries_dir + "test/", sess.graph)

    # Initializing the variables
    init = tf.global_variables_initializer()
    for v in tf.trainable_variables():
        print v.name
    sess.run(init)
    test_len = 128
    test_data = mnist.test.images[:test_len].reshape((-1, n_steps, n_input))
    test_label = mnist.test.labels[:test_len]
    step = 1
    
    dau_counter = 0
    grad_vals = []
    # Keep training until reach max iterations
    while step * batch_size < training_iters:
        batch_x, batch_y = mnist.train.next_batch(batch_size)
        batch_x = batch_x.reshape([batch_size, n_steps, n_input])
        streaming_norm_training_mode_global_flag = True
        
        #sess.run(apply_grads, feed_dict={x: batch_x, y: batch_y})
        grad_vals.append(sess.run([grad[0] for grad in grads], feed_dict={x: batch_x, y: batch_y}))
        dau_counter += 1
        if dau_counter == n_dau:
            dau_counter = 0
            feed = {}
            for i in range(len(grad_vals[0])):
                feed[grad_placeholder[i][0]] = grad_vals[0][i]
                for j in range(1, n_dau):
                    feed[grad_placeholder[i][0]] += grad_vals[j][i]
                feed[grad_placeholder[i][0]] /= n_dau
            sess.run(apply_grads, feed_dict=feed)
            grad_vals = []
            if tensorboard:
                summary = sess.run(merged, feed_dict={x: batch_x, y: batch_y})
                train_writer.add_summary(summary, step)

        if step % display_step == 0:
            # Calculate batch accuracy
            if tensorboard:
                summary, acc, loss = sess.run([merged, accuracy, cost], feed_dict={x: batch_x, y: batch_y})
                train_writer.add_summary(summary, step)
            else:
                acc, loss = sess.run([accuracy, cost], feed_dict={x: batch_x, y: batch_y})
                
            # Calculate batch loss
            print "Iter " + str(step * batch_size) + ", Minibatch Loss= " + \
                "{:.6f}".format(loss) + ", Training Accuracy= " + \
                "{:.5f}".format(acc)
            streaming_norm_training_mode_global_flag = False

            if tensorboard:
                summary, acc, loss = sess.run([merged, accuracy, cost], feed_dict={x: test_data, y: test_label})
                test_writer.add_summary(summary, step)
            else:
                acc, loss = sess.run([accuracy, cost], feed_dict={x: test_data, y: test_label})

            print "Testing Accuracy:", acc
        step += 1
    print "Optimization Finished!"

    # Calculate accuracy for 128 mnist test images

    print "Testing Accuracy:", \
        sess.run(accuracy, feed_dict={x: test_data, y: test_label})


def main(_):
    train()


if __name__ == '__main__':
    tf.app.run()
