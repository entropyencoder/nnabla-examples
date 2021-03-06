# Copyright (c) 2017 Sony Corporation. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from six.moves import range

import os

import nnabla as nn
import nnabla.logger as logger
import nnabla.functions as F
import nnabla.parametric_functions as PF
import nnabla.solvers as S
import nnabla.utils.save as save

from args import get_args
from mnist_data import data_iterator_mnist


def categorical_error(pred, label):
    """
    Compute categorical error given score vectors and labels as
    numpy.ndarray.
    """
    pred_label = pred.argmax(1)
    return (pred_label != label.flat).mean()


def mnist_lenet_prediction(image, test=False):
    """
    Construct LeNet for MNIST.
    """
    image /= 255.0
    c1 = PF.convolution(image, 16, (5, 5), name='conv1')
    c1 = F.relu(F.max_pooling(c1, (2, 2)), inplace=True)
    c2 = PF.convolution(c1, 16, (5, 5), name='conv2')
    c2 = F.relu(F.max_pooling(c2, (2, 2)), inplace=True)
    c3 = F.relu(PF.affine(c2, 50, name='fc3'), inplace=True)
    c4 = PF.affine(c3, 10, name='fc4')
    return c4


def mnist_resnet_prediction(image, test=False):
    """
    Construct ResNet for MNIST.
    """
    image /= 255.0

    def bn(x):
        return PF.batch_normalization(x, batch_stat=not test)

    def res_unit(x, scope):
        C = x.shape[1]
        with nn.parameter_scope(scope):
            with nn.parameter_scope('conv1'):
                h = F.elu(bn(PF.convolution(x, C / 2, (1, 1), with_bias=False)))
            with nn.parameter_scope('conv2'):
                h = F.elu(
                    bn(PF.convolution(h, C / 2, (3, 3), pad=(1, 1), with_bias=False)))
            with nn.parameter_scope('conv3'):
                h = bn(PF.convolution(h, C, (1, 1), with_bias=False))
        return F.elu(F.add2(h, x, inplace=True))
    # Conv1 --> 64 x 32 x 32
    with nn.parameter_scope("conv1"):
        c1 = F.elu(
            bn(PF.convolution(image, 64, (3, 3), pad=(3, 3), with_bias=False)))
    # Conv2 --> 64 x 16 x 16
    c2 = F.max_pooling(res_unit(c1, "conv2"), (2, 2))
    # Conv3 --> 64 x 8 x 8
    c3 = F.max_pooling(res_unit(c2, "conv3"), (2, 2))
    # Conv4 --> 64 x 8 x 8
    c4 = res_unit(c3, "conv4")
    # Conv5 --> 64 x 4 x 4
    c5 = F.max_pooling(res_unit(c4, "conv5"), (2, 2))
    # Conv5 --> 64 x 4 x 4
    c6 = res_unit(c5, "conv6")
    pl = F.average_pooling(c6, (4, 4))
    with nn.parameter_scope("classifier"):
        y = PF.affine(pl, 10)
    return y


#def train():
#    """
#    Main script.
#
#    Steps:
#
#    * Parse command line arguments.
#    * Specify a context for computation.
#    * Initialize DataIterator for MNIST.
#    * Construct a computation graph for training and validation.
#    * Initialize a solver and set parameter variables to it.
#    * Create monitor instances for saving and displaying training stats.
#    * Training loop
#      * Computate error rate for validation data (periodically)
#      * Get a next minibatch.
#      * Execute forwardprop on the training graph.
#      * Compute training error
#      * Set parameter gradients zero
#      * Execute backprop.
#      * Solver updates parameters by using gradients computed by backprop.
#    """
#    args = get_args()
#
#    # Get context.
#    from nnabla.contrib.context import extension_context
#    extension_module = args.context
#    if args.context is None:
#        extension_module = 'cpu'
#    logger.info("Running in %s" % extension_module)
#    ctx = extension_context(extension_module, device_id=args.device_id)
#    nn.set_default_context(ctx)
#
#    # Create CNN network for both training and testing.
#    mnist_cnn_prediction = mnist_lenet_prediction
#    if args.net == 'resnet':
#        mnist_cnn_prediction = mnist_resnet_prediction
#
#    # TRAIN
#    # Create input variables.
#    image = nn.Variable([args.batch_size, 1, 28, 28])
#    label = nn.Variable([args.batch_size, 1])
#    # Create prediction graph.
#    pred = mnist_cnn_prediction(image, test=False)
#    pred.persistent = True
#    # Create loss function.
#    loss = F.mean(F.softmax_cross_entropy(pred, label))
#
#    # TEST
#    # Create input variables.
#    vimage = nn.Variable([args.batch_size, 1, 28, 28])
#    vlabel = nn.Variable([args.batch_size, 1])
#    # Create predition graph.
#    vpred = mnist_cnn_prediction(vimage, test=True)
#
#    # Create Solver.
#    solver = S.Adam(args.learning_rate)
#    solver.set_parameters(nn.get_parameters())
#
#    # Create monitor.
#    from nnabla.monitor import Monitor, MonitorSeries, MonitorTimeElapsed
#    monitor = Monitor(args.monitor_path)
#    monitor_loss = MonitorSeries("Training loss", monitor, interval=10)
#    monitor_err = MonitorSeries("Training error", monitor, interval=10)
#    monitor_time = MonitorTimeElapsed("Training time", monitor, interval=100)
#    monitor_verr = MonitorSeries("Test error", monitor, interval=10)
#
#    # Initialize DataIterator for MNIST.
#    data = data_iterator_mnist(args.batch_size, True)
#    vdata = data_iterator_mnist(args.batch_size, False)
#    # Training loop.
#    for i in range(args.max_iter):
#        if i % args.val_interval == 0:
#            # Validation
#            ve = 0.0
#            for j in range(args.val_iter):
#                vimage.d, vlabel.d = vdata.next()
#                vpred.forward(clear_buffer=True)
#                ve += categorical_error(vpred.d, vlabel.d)
#            monitor_verr.add(i, ve / args.val_iter)
#        if i % args.model_save_interval == 0:
#            nn.save_parameters(os.path.join(
#                args.model_save_path, 'params_%06d.h5' % i))
#        # Training forward
#        image.d, label.d = data.next()
#        solver.zero_grad()
#        loss.forward(clear_no_need_grad=True)
#        loss.backward(clear_buffer=True)
#        solver.weight_decay(args.weight_decay)
#        solver.update()
#        e = categorical_error(pred.d, label.d)
#        monitor_loss.add(i, loss.d.copy())
#        monitor_err.add(i, e)
#        monitor_time.add(i)
#
#    ve = 0.0
#    for j in range(args.val_iter):
#        vimage.d, vlabel.d = vdata.next()
#        vpred.forward(clear_buffer=True)
#        ve += categorical_error(vpred.d, vlabel.d)
#    monitor_verr.add(i, ve / args.val_iter)
#
#    parameter_file = os.path.join(
#        args.model_save_path, '{}_params_{:06}.h5'.format(args.net, args.max_iter))
#    nn.save_parameters(parameter_file)

def test():
    print ("Evaluate the trained model with full MNIST test set")
    
    args = get_args()
    
    # Create CNN network for both training and testing.
    mnist_cnn_prediction = mnist_lenet_prediction
    if args.net == 'resnet':
        mnist_cnn_prediction = mnist_resnet_prediction

    args.batch_size = 100
    tdata = data_iterator_mnist (args.batch_size, False)
    timage = nn.Variable ([args.batch_size, 1, 28, 28])
    tlabel = nn.Variable ([args.batch_size, 1])

    parameter_file = os.path.join(
        args.model_save_path, '{}_params_{:06}.h5'.format(args.net, args.max_iter))
    nn.load_parameters(parameter_file)
    
    # Create inference graph 
    tpred = mnist_cnn_prediction (timage, test = True)
    num_test_iter = int ((tdata.size + args.batch_size - 1) / args.batch_size)
    
    te = 0.0
    
    for j in range (num_test_iter):
        timage.d, tlabel.d = tdata.next ()
        tpred.forward (clear_buffer=True)
        te += categorical_error (tpred.d, tlabel.d)

    te_avg = te / num_test_iter
    print ("MNIST test accuracy", 1 - te_avg)
    
    # # Another testing implementation (same result as the above)
    # monitor_terr = M.MonitorSeries ("Test error", monitor, interval=num_test_iter)
    # for j in range(num_test_iter):
    #   timage.d, tlabel.d = tdata.next()
    #   tpred.forward (clear_buffer=True)
    #   monitor_terr.add (j, categorical_error (tpred.d, tlabel.d))


if __name__ == '__main__':
    #train()
    test()
