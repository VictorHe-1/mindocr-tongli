from mindspore import nn
import mindspore as ms
import mindspore.ops as ops
from mindspore.communication import get_group_size
from mindspore.common import dtype as mstype
from mindspore.ops import functional as F


class NetWithLossWrapper(nn.Cell):
    '''
    A universal wrapper for any network with any loss.

    Args:
        net (nn.Cell): network
        loss_fn: loss function
        input_indices: The indices of the data tuples which will be fed into the network. If it is None, then the first item will be fed only.
        label_indices: The indices of the data tuples which will be fed into the loss function. If it is None, then the remaining items will be fed.
    '''
    def __init__(self, net, loss_fn, pred_cast_fp32=False, input_indices=None, label_indices=None):
        super().__init__(auto_prefix=False)
        self._net = net
        self._loss_fn = loss_fn
        # TODO: get this automatically from net and loss func
        self.input_indices = input_indices
        self.label_indices = label_indices
        self.pred_cast_fp32 = pred_cast_fp32

    def construct(self, *args):
        '''
        Args:
            args (Tuple): contains network inputs, labels (given by data loader)
        Returns:
            loss_val (Tensor): loss value
        '''
        if self.input_indices is None:
            pred = self._net(args[0])
        else:
            pred = self._net(*select_inputs_by_indices(args, self.input_indices))

        if self.pred_cast_fp32:
            if isinstance(pred, ms.Tensor):
                pred = F.cast(pred, mstype.float32)
            else:
                pred = [F.cast(p, mstype.float32) for p in pred]

        if self.label_indices is None:
            loss_val = self._loss_fn(pred, *args[1:])
        else:
            label = select_inputs_by_indices(args, self.label_indices)
            loss_val = self._loss_fn(pred, label)

        return loss_val


class NetWithEvalWrapper(nn.Cell):
    '''
    A universal wrapper for any network with any loss for evaluation pipeline.
    Difference from NetWithLossWrapper: it returns loss_val, pred, and labels.

    Args:
        net (nn.Cell): network
        loss_fn: loss function, if None, will not compute loss for evaluation dataset
        input_indices: The indices of the data tuples which will be fed into the network. If it is None, then the first item will be fed only.
        label_indices: The indices of the data tuples which will be fed into the loss function. If it is None, then the remaining items will be fed.
    '''
    def __init__(self, net, loss_fn=None, input_indices=None, label_indices=None):
        super().__init__(auto_prefix=False)
        self._net = net
        self._loss_fn = loss_fn
        # TODO: get this automatically from net and loss func
        self.input_indices = input_indices
        self.label_indices = label_indices

    def construct(self, *args):
        '''
        Args:
            args (Tuple): contains network inputs, labels (given by data loader)
        Returns:
            Tuple: loss value (Tensor), pred (Union[Tensor, Tuple[Tensor]]), labels (Tuple)
        '''
        # TODO: pred is a dict
        if self.input_indices is None:
            pred = self._net(args[0])
        else:
            pred = self._net(*select_inputs_by_indices(args, self.input_indices))

        if self.label_indices is None:
            labels = args[1:]
        else:
            labels = select_inputs_by_indices(args, self.label_indices)

        if self._loss_fn is not None:
            loss_val = self._loss_fn(pred, *labels)
        else:
            loss_val = None

        return loss_val, pred, labels

def select_inputs_by_indices(inputs, indices):
    new_inputs = list()
    for x in indices:
        new_inputs.append(inputs[x])
    return new_inputs
