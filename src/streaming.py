# Liang Zhou

import tensorflow as tf
from tensorflow.python.framework import ops
import numpy as np

def stream(x, name, training_mode=False):
    with tf.variable_scope(name) as scope:
        # this should be the same as not doing any streaming things
        alpha = [0,1]
        beta = [0,0.3,0,7]
        kappa = alpha * 2
        x_shape = x.get_shape();

        # defining normstats streaming variables
        s_long  = tf.get_variable('s_long',shape=x_shape,trainable=False,initializer=tf.constant_initializer(0))
        s_short  = tf.get_variable('s_short',shape=x_shape,trainable=False,initializer=tf.constant_initializer(0))
        s_final  = tf.get_variable('s_final',shape=x_shape,trainable=False)
        s_short_counter  = tf.get_variable('s_short_counter',shape=[],trainable=False)
        s_w_updated_flag  = tf.get_variable('s_w_updated_flag',shape=[],trainable=True,initializer=tf.constant_initializer(1))
        g_w_updated_flag  = tf.get_variable('g_w_updated_flag',shape=[],trainable=True,initializer=tf.constant_initializer(1))

        update_streaming(x,s_long,s_short,s_final,s_short_counter,s_w_updated_flag,alpha[0:2],kappa[0:2])
 
        x_revised = py_func_with_grad(lambda s: s, [s_final], [tf.float32], name=name, grad=lambda op,grad: stream_gradient(op,grad,name,beta,kappa))
        # force some gradient onto the flags
        x_revised = tf.add(x_revised, force_gradient(s_w_updated_flag,1))
        x_revised = tf.add(x_revised, force_gradient(g_w_updated_flag,1))

        # reshape because otherwise it breaks
        x_revised = tf.reshape(x_revised, x.get_shape())
        return x_revised
    

def stream_gradient(op, grad, name, beta, kappa):
    with tf.variable_scope(name) as scope:
        x = op.inputs[0]

        # same as with normstats but with gradients
        g_long  = get_variable('g_long',shape=x.get_shape(),trainable=False,initializer=tf.constant_initializer(0))
        g_short = get_variable('g_short',shape=x.get_shape(),trainable=False,initializer=tf.constant_initializer(0))
        g_final = get_variable('g_final',shape=x.get_shape(),trainable=False)
        g_short_counter = get_variable('g_short_counter',shape=[],trainable=False, initializer=tf.constant_initializer(0))
        g_w_updated_flag  = get_variable('g_w_updated_flag',shape=[],trainable=True, initializer=tf.constant_initializer(1))

        update_streaming(grad,g_long,g_short,g_final,g_short_counter,g_w_updated_flag,beta[0:2],kappa[2:4])

        # final g to use based on streaming norm gradient update equation
        g_combined = g_final + beta[2] * grad

        # assign this final value to g_final
        g_final.assign(g_combined)
        return tf.convert_to_tensor(g_combined)



def update_streaming(x, v_long, v_short, v_final, v_short_counter,v_w_updated_flag, alpha_beta, kappa):
    x = tf.stop_gradient(x)
    proceed = True
    zero = tf.constant(0.0)
    zero_short = tf.constant(0.0, shape=v_short.get_shape())
    one = tf.constant(1.0)
    true = tf.constant(True, dtype=tf.bool)
    false = tf.constant(False, dtype=tf.bool)
    if proceed:
        # update short variable
        v_short.assign(v_short*v_short_counter + x)

        def update_long():
            def update_first():
                #print 'first update'
                return v_long.assign(v_short)
            def update_rest():
                #print 'not first update'
                return v_long.assign(v_long*kappa[0] + v_short*kappa[1])

            # check whether long has been updated before by seeing if it's equal to 0
            v_long_is_0 = tf.equal(v_long, zero)[0][0]
            tf.cond(v_long_is_0, update_first, update_rest)

            # now the weight has been updated, assign 0 to the flag
            v_w_updated_flag.assign(zero)

            # reset weight of short variable to 0
            v_short.assign(zero_short)
            #print 'assigned 0 to short'
            return true

        # check if weight has been updated; if so, update, if not, don't do anything
        tf.cond(tf.equal(v_w_updated_flag, one), update_long, lambda: true)
        #print 'assigning more stuff'
        v_short_counter_updated = v_short_counter.assign_add(1)
        v_short.assign(v_short / v_short_counter_updated)

        v_final.assign(v_long*alpha_beta[0] + v_short*alpha_beta[1])


# define gradient of a python function
def py_func_with_grad(func, inp, Tout, stateful=True, name=None, grad=None):
    num = []
    for i in range(100):
        num.append(str(np.random.randint(0,10)))
    rnd_name = 'PyFuncGrad' + ''.join(num)
    tf.RegisterGradient(rnd_name)(grad)
    g = tf.get_default_graph()
    with g.gradient_override_map({"PyFunc": rnd_name}):
        return tf.py_func(func, inp, Tout, stateful=stateful, name=name)

# force a gradient to be considered in computation graph
def force_gradient(x,mag,name='force_grad'):
    # this op forwardprops 0, backprops mag
    return py_func_with_grad(lambda x: np.float32(0),[x],[tf.float32],name=name,grad=lambda op, grad: force_grad_backprop(op,grad,mag))

# forace that gradient to be 0
def force_grad_backprop(op,grad,mag):
    # backprop a constant gradient
    x = op.inputs[0]
    return x*0+mag

