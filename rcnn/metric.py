#-*-coding=utf-8-*-
import mxnet as mx
import numpy as np

from rcnn.config import config


class AccuracyMetric(mx.metric.EvalMetric):
    def __init__(self, use_ignore=False, ignore=None):
        super(AccuracyMetric, self).__init__('Accuracy')
        self.use_ignore = use_ignore
        self.ignore = ignore
        self.has_rpn = config.TRAIN.HAS_RPN
        if self.has_rpn:
            assert self.use_ignore and self.ignore is not None
    # 根据labels 和 preds计算准确率
    def update(self, labels, preds):
        if self.has_rpn:
            pred_label = mx.ndarray.argmax_channel(preds[0]).asnumpy().astype('int32')
            label = labels[0].asnumpy().astype('int32')
            non_ignore_inds = np.where(label != self.ignore)
            pred_label = pred_label[non_ignore_inds]
            label = label[non_ignore_inds]
        else:
            last_dim = preds[0].shape[-1] #一个实例的在各个类上的预测值
            # 预测值最大的数值所在的索引即为该预测类别的标号
            pred_label = preds[0].asnumpy().reshape(-1, last_dim).argmax(axis=1).astype('int32')
            # 扁平化类别编号
            label = labels[0].asnumpy().reshape(-1,).astype('int32')

        self.sum_metric += (pred_label.flat == label.flat).sum()
        self.num_inst += len(pred_label.flat)


class LogLossMetric(mx.metric.EvalMetric):
    def __init__(self, use_ignore=False, ignore=None):
        super(LogLossMetric, self).__init__('LogLoss')
        self.use_ignore = use_ignore
        self.ignore = ignore
        self.has_rpn = config.TRAIN.HAS_RPN
        if self.has_rpn:
            assert self.use_ignore and self.ignore is not None

    def update(self, labels, preds):
        if self.has_rpn:
            pred_cls = preds[0].asnumpy()[0]
            label = labels[0].asnumpy().astype('int32')[0]
            non_ignore_inds = np.where(label != self.ignore)[0]
            label = label[non_ignore_inds]
            cls = pred_cls[label, non_ignore_inds]
        else:
            last_dim = preds[0].shape[-1]
            pred_cls = preds[0].asnumpy().reshape(-1, last_dim)
            label = labels[0].asnumpy().reshape(-1,).astype('int32')
            # 每个label中的一个元素对应于pred_cls中的一行，其中label的值，和pred_cls中一行数据下标对应
            """
            a=np.array([[1,2,5],[4,6,7]])
            la=np.array([1,0])
            cls=a[np.arange(la.shape[0],la)]
            cls的结果:arrany([2,4])
            """
            cls = pred_cls[np.arange(label.shape[0]), label]
        cls += config.EPS #1e-14
        cls_loss = -1 * np.log(cls)
        cls_loss = np.sum(cls_loss)
        self.sum_metric += cls_loss
        self.num_inst += label.shape[0]


class SmoothL1LossMetric(mx.metric.EvalMetric):
    def __init__(self):
        super(SmoothL1LossMetric, self).__init__('SmoothL1Loss')
        self.has_rpn = config.TRAIN.HAS_RPN

    def update(self, labels, preds):
        # preds 是一个[batch_size=2, -1, 21*4=84]的一个3维数组，其中第一维代表的是几个
        # 图片，第二维是一个图片上的rois，第三个是回归位置值
        bbox_loss = preds[1].asnumpy()
        if self.has_rpn:
            bbox_loss = bbox_loss.reshape((bbox_loss.shape[0], -1))
        else:
            # 注意bbox_loss
            first_dim = bbox_loss.shape[0] * bbox_loss.shape[1]
            bbox_loss = bbox_loss.reshape(first_dim, -1)
        self.num_inst += bbox_loss.shape[0]
        bbox_loss = np.sum(bbox_loss)
        self.sum_metric += bbox_loss
