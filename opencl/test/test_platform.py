'''
Created on Sep 27, 2011

@author: sean
'''

from opencl import Platform, get_platforms, Context, Device, Queue, Program, DeviceMemoryView, empty
from opencl import ContextProperties, global_memory, UserEvent, Event
from opencl.kernel import parse_args

import unittest
import ctypes
import numpy as np
import gc
import time
from threading import Event as PyEvent

source = """

__kernel void generate_sin(__global float2* a, float scale)
{
    int id = get_global_id(0);
    int n = get_global_size(0);
    float r = (float)id / (float)n;
    
    a[id].x = id;
    a[id].y = native_sin(r) * scale;
}
"""

class Test(unittest.TestCase):
    
    
    def test_get_platforms(self):
        platforms = get_platforms()

    def test_get_devices(self):
        plat = get_platforms()[0]
        devices = plat.devices()
        native_kernels = [dev.native_kernel for dev in devices]

    def test_context(self):
        
        ctx = Context(device_type=Device.CPU)
        
    
    def test_create_queue(self):
        
        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])

        global foo
        
        foo = 0
        
        def incfoo(arg, op=lambda a, b: 0):
            global foo
            foo = op(foo, arg)
            
        queue.enqueue_native_kernel(incfoo, 4, op=lambda a, b: a + b)
        queue.enqueue_native_kernel(incfoo, 3, op=lambda a, b: a * b)
        
        queue.finish()
        
        self.assertEqual(foo, 12)

class TestContext(unittest.TestCase):
    def test_properties(self):
        platform = get_platforms()[0]
        
        properties = ContextProperties()
        
        properties.platform = platform
        
        self.assertEqual(platform.name, properties.platform.name)
        
        ctx = Context(device_type=Device.CPU, properties=properties)

class TestProgram(unittest.TestCase):
        
    def test_program(self):
        ctx = Context(device_type=Device.CPU)
        
        program = Program(ctx, source=source)
        
        program.build()
        
    def test_devices(self):
        ctx = Context(device_type=Device.CPU)
        
        program = Program(ctx, source=source)
        
        program.build()
        
class TestKernel(unittest.TestCase):
    
    def test_name(self):
        ctx = Context(device_type=Device.CPU)
        program = Program(ctx, source=source)
        
        program.build()
        
        generate_sin = program.kernel('generate_sin')
        
        self.assertEqual(generate_sin.name, 'generate_sin')
        
    def test_argtypes(self):

        ctx = Context(device_type=Device.CPU)
        program = Program(ctx, source=source)
        
        program.build()
        
        generate_sin = program.kernel('generate_sin')
        
        generate_sin.argtypes = [DeviceMemoryView, ctypes.c_float]
        
        with self.assertRaises(TypeError):
            generate_sin.argtypes = [DeviceMemoryView, ctypes.c_float, ctypes.c_float]

    def test_set_args(self):

        ctx = Context(device_type=Device.CPU)
        program = Program(ctx, source=source)
        
        program.build()
        
        generate_sin = program.kernel('generate_sin')
        
        generate_sin.argtypes = [global_memory(), ctypes.c_float]
        
        buf = empty(ctx, [10], ctype='ff')
        
        queue = Queue(ctx, ctx.devices[0])
        
        generate_sin.set_args(buf, 1.0)
        queue.enqueue_nd_range_kernel(generate_sin, 1, global_work_size=[buf.size])
        
        expected = np.zeros([10], dtype=[('x', np.float32), ('y', np.float32)])
        expected['x'] = np.arange(10)
        expected['y'] = np.sin(expected['x'] / 10)
        
        with buf.map(queue) as host:
            self.assertTrue(np.all(expected['x'] == np.asarray(host)['f0']))
            self.assertTrue(np.all(expected['y'] == np.asarray(host)['f1']))

        generate_sin.argnames = ['a', 'scale']
        generate_sin.set_args(a=buf, scale=1.0)
        queue.enqueue_nd_range_kernel(generate_sin, 1, global_work_size=[buf.size])
        
        with buf.map(queue) as host:
            self.assertTrue(np.all(expected['x'] == np.asarray(host)['f0']))
            self.assertTrue(np.all(expected['y'] == np.asarray(host)['f1']))
            
        with self.assertRaises(TypeError):
            generate_sin.set_args(a=buf)
            
        generate_sin.__defaults__ = [1.0]
        generate_sin.set_args(a=buf)
        
        queue.enqueue_nd_range_kernel(generate_sin, 1, global_work_size=[buf.size])
        
        with buf.map(queue) as host:
            self.assertTrue(np.all(expected['x'] == np.asarray(host)['f0']))
            self.assertTrue(np.all(expected['y'] == np.asarray(host)['f1']))

    def test_call(self):

        expected = np.zeros([10], dtype=[('x', np.float32), ('y', np.float32)])
        expected['x'] = np.arange(10)
        expected['y'] = np.sin(expected['x'] / 10)
        
        ctx = Context(device_type=Device.CPU)
        program = Program(ctx, source=source)
        
        program.build()
        
        generate_sin = program.kernel('generate_sin')
        
        generate_sin.argtypes = [global_memory(), ctypes.c_float]
        
        buf = empty(ctx, [10], ctype='ff')
        
        queue = Queue(ctx, ctx.devices[0])
        
        size = [buf.size]
        with self.assertRaises(TypeError):
            generate_sin(queue, buf, 1.0)
        
        generate_sin(queue, buf, 1.0, global_work_size=size)
        
        with buf.map(queue) as host:
            self.assertTrue(np.all(expected['x'] == np.asarray(host)['f0']))
            self.assertTrue(np.all(expected['y'] == np.asarray(host)['f1']))

        generate_sin.global_work_size = lambda a, scale: [a.size]
        
        generate_sin(queue, buf, 1.0)
        
        with buf.map(queue) as host:
            self.assertTrue(np.all(expected['x'] == np.asarray(host)['f0']))
            self.assertTrue(np.all(expected['y'] == np.asarray(host)['f1']))

    def test_parse_args(self):
        
        arglist = parse_args('test', (1, 2, 3), dict(d=4, e=5), ('a', 'b', 'c', 'd', 'e'), ())
        self.assertEqual(arglist, (1, 2, 3, 4, 5))

        arglist = parse_args('test', (1, 2, 3), dict(), ('a', 'b', 'c', 'd', 'e'), (4, 5))
        self.assertEqual(arglist, (1, 2, 3, 4, 5))

        arglist = parse_args('test', (1, 2), dict(c=3), ('a', 'b', 'c', 'd', 'e'), (4, 5))
        self.assertEqual(arglist, (1, 2, 3, 4, 5))

        arglist = parse_args('test', (1, 2), dict(c=3, d=5), ('a', 'b', 'c', 'd', 'e'), (4, 5))
        self.assertEqual(arglist, (1, 2, 3, 5, 5))

        arglist = parse_args('test', (1, 2), dict(c=6, d=6), ('a', 'b', 'c', 'd', 'e'), (4, 5))
        self.assertEqual(arglist, (1, 2, 6, 6, 5))

        arglist = parse_args('test', (), dict(), ('a', 'b', 'c', 'd', 'e'), (1, 2, 3, 4, 5))
        self.assertEqual(arglist, (1, 2, 3, 4, 5))

        
        arglist = parse_args('test', (1, 2, 3, 4, 5), dict(), ('a', 'b', 'c', 'd', 'e'), ())
        self.assertEqual(arglist, (1, 2, 3, 4, 5))
        
        arglist = parse_args('test', (), dict(a=1, b=2, c=3, d=4, e=5), ('a', 'b', 'c', 'd', 'e'), ())
        self.assertEqual(arglist, (1, 2, 3, 4, 5))
        
        with self.assertRaises(TypeError):
            arglist = parse_args('test', (), dict(), ('a', 'b'), ())

        with self.assertRaises(TypeError):
            arglist = parse_args('test', (1), dict(a=1), ('a', 'b'), ())

        with self.assertRaises(TypeError):
            arglist = parse_args('test', (), dict(b=1), ('a', 'b'), (2))
            
        with self.assertRaises(TypeError):
            arglist = parse_args('test', (1, 2, 3), dict(), ('a', 'b'), ())
        
class TestBuffer(unittest.TestCase):
    
    def test_size(self):     
        
        ctx = Context(device_type=Device.CPU)   
        buf = empty(ctx, [4])
        
        self.assertEqual(buf._refcount, 1)
        
        self.assertEqual(len(buf), 4 / buf.itemsize)
        self.assertEqual(buf.mem_size, 4)
        
    def test_from_host(self):
        ctx = Context(device_type=Device.CPU)
        a = np.array([[1, 2], [3, 4]])
        view_a = memoryview(a)
        clmem = DeviceMemoryView.from_host(ctx, a)
        
        self.assertEqual(clmem.format, view_a.format)
        self.assertEqual(clmem.shape, view_a.shape)
        self.assertEqual(clmem.strides, view_a.strides)
        
    def test_read_write(self):
        ctx = Context(device_type=Device.CPU)   
        a = np.array([[1, 2], [3, 4]])
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        queue = Queue(ctx, ctx.devices[0])
        
        out = np.zeros_like(a)
        
        clbuf.read(queue, out, blocking=True)
        
        self.assertTrue(np.all(out == a))
        
        clbuf.write(queue, a + 1, blocking=True)

        clbuf.read(queue, out, blocking=True)
        
        self.assertTrue(np.all(out == a + 1))
        
    def test_map(self):
        
        ctx = Context(device_type=Device.CPU)   
        a = np.array([[1, 2], [3, 4]])
        view_a = memoryview(a)
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
    
        queue = Queue(ctx, ctx.devices[0])
        
        self.assertEqual(clbuf._mapcount, 0)
        
        with clbuf.map(queue, readonly=True) as buf:
            self.assertEqual(clbuf._mapcount, 1)
        
            self.assertEqual(buf.format, view_a.format)
            self.assertEqual(buf.shape, view_a.shape)
            self.assertEqual(buf.strides, view_a.strides)
            
            b = np.asarray(buf)
            self.assertTrue(np.all(b == a))
        
            self.assertTrue(buf.readonly)
        
#        self.assertEqual(clbuf._mapcount, 0)
        
        with clbuf.map(queue) as buf:
            self.assertEqual(clbuf._mapcount, 1)
            b = np.asarray(buf)
            b[::] = b[::-1]
            
            self.assertFalse(buf.readonly)
            
#        self.assertEqual(clbuf._mapcount, 0)
        
        with clbuf.map(queue, readonly=True) as buf:
            self.assertEqual(clbuf._mapcount, 1)
            b = np.asarray(buf)
            self.assertTrue(np.all(b == a[::-1]))
            
    def test_refcount(self):

        ctx = Context(device_type=Device.CPU)
        a = np.array([[1, 2], [3, 4]])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)

        self.assertEqual(clbuf._refcount, 1)
        
        new_buf = clbuf[:, :-1]
        
        self.assertEqual(clbuf._refcount, 2)
        
        del new_buf
        
        self.assertEqual(clbuf._refcount, 1)
        
        
    def test_get_slice(self):
        
        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.array([1, 2, 3, 4])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)

        self.assertEqual(clbuf._refcount, 1)
        
        new_buf = clbuf[::2]
        
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[::2]))
            
        new_buf = clbuf[1::2]
        
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[1::2]))

        new_buf = clbuf[::-1]
        
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[::-1]))
            
        
    def test_getitem(self):

        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.array([[1, 2], [3, 4]])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)

        with self.assertRaises(IndexError):
            clbuf[1, 1, 1]
        
        self.assertEqual(clbuf._refcount, 1)
        
        new_buf = clbuf[:, :-1]
        
        self.assertEqual(clbuf._refcount, 2)
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[:, :-1]))
            
            
        del buf, new_buf
        gc.collect()
        
        self.assertEqual(clbuf._refcount, 1)
        
        new_buf = clbuf[:, 1:]
        
        self.assertEqual(clbuf._refcount, 2)
        
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[:, 1:]))

        new_buf = clbuf[1:, :]
        
        with new_buf.map(queue) as buf:
            b = np.asanyarray(buf)
            self.assertTrue(np.all(b == a[1:, :]))
        
    def test_is_contiguous(self):
        
        ctx = Context(device_type=Device.CPU)
        a = np.array([[1, 2], [3, 4]])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        self.assertTrue(clbuf.is_contiguous)
        
        self.assertFalse(clbuf[:, 1:].is_contiguous)
        self.assertFalse(clbuf[::2, :].is_contiguous)
        self.assertFalse(clbuf[:, ::2].is_contiguous)
        
    def test_copy_contig(self):

        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.array([[1, 2], [3, 4]])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        copy_of = clbuf.copy(queue)
        queue.barrier()
        with copy_of.map(queue) as cpy:
            b = np.asarray(cpy)
            self.assertTrue(np.all(a == b))
            
    def test_copy_1D(self):

        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.array([1, 2, 3, 4])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        copy_of = clbuf[::2].copy(queue)
            
        with copy_of.map(queue) as cpy:
            b = np.asarray(cpy)
            self.assertTrue(np.all(a[::2] == b))
            
        copy_of = clbuf[1::2].copy(queue)
            
        with copy_of.map(queue) as cpy:
            b = np.asarray(cpy)
            self.assertTrue(np.all(a[1::2] == b))
            
        copy_of = clbuf[1:-1].copy(queue)
            
        with copy_of.map(queue) as cpy:
            b = np.asarray(cpy)
            self.assertTrue(np.all(a[1:-1] == b))

    def test_copy_2D(self):


        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.arange(6 * 6).reshape([6, 6])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        slices = [
                  (slice(None, None, 2), slice(None, None, 2)),
                  (slice(1, None, None), slice(1, None, None)),
                  (slice(None, None, None), slice(1, None, None)),
                  (slice(1, None, None), slice(None, None, None)),
                  
                  (slice(1, None, None), slice(0, None, 2)),
                  (slice(None, None, 2), slice(1, None, 2)),
                  (slice(1, None, 2), slice(None, None, 2)),
                  ]
        
        for idx0, idx1 in slices:
            
            expected = a[idx0, idx1]
            sub_buf = clbuf[idx0, idx1]
            copy_of = sub_buf.copy(queue)
        
            with copy_of.map(queue) as cpy:
                b = np.asarray(cpy)
                expected = a[idx0, idx1]
                
                self.assertTrue(np.all(expected == b), (idx0, idx1))
                
    @unittest.expectedFailure     
    def test_copy_2D_negative_stride(self):


        ctx = Context(device_type=Device.CPU)
        queue = Queue(ctx, ctx.devices[0])   
        a = np.arange(4 * 4).reshape([4, 4])
        
        clbuf = DeviceMemoryView.from_host(ctx, a)
        
        slices = [(slice(None, None, -2), slice(None, None, -2)),
                  
                  (slice(1, None, -1), slice(1, None, -1)),
                  (slice(None, None, None), slice(1, None, -1)),
                  (slice(1, None, -1), slice(None, None, -1)),
                  
                  (slice(1, None, -2), slice(1, None, -2)),
                  (slice(None, None, -2), slice(1, None, -2)),
                  (slice(1, None, -2), slice(None, None, -2)),
                  ]
        
        for idx0, idx1 in slices:
            copy_of = clbuf[idx0, idx1].copy(queue)
        
            with copy_of.map(queue) as cpy:
                b = np.asarray(cpy)
                expected = a[idx0, idx1]
                self.assertTrue(np.all(expected == b))

        
class TestEvent(unittest.TestCase):
    
    def test_status(self):
        
        
        ctx = Context(device_type=Device.DEFAULT)
        event = UserEvent(ctx)
        
        self.assertEqual(event.status, Event.SUBMITTED)
        event.complete()
        self.assertEqual(event.status, Event.COMPLETE)
        
    def test_wait(self):
        
        ctx = Context(device_type=Device.DEFAULT)
        event = UserEvent(ctx)

        queue = Queue(ctx, ctx.devices[0])
        
        queue.wait(event)
        
        event2 = queue.marker()
        
        self.assertEqual(event.status, Event.SUBMITTED)
        self.assertEqual(event2.status, Event.QUEUED)
        
        event.complete()
        self.assertEqual(event.status, Event.COMPLETE)
        
        event2.wait()
        self.assertEqual(event2.status, Event.COMPLETE)

    def test_callback(self):
        self.callback_called = False
        self.py_event = PyEvent()
        
        def callback(event, status):
            self.callback_called = True
            self.py_event.set()
        
        ctx = Context(device_type=Device.DEFAULT)
        event = UserEvent(ctx)

        queue = Queue(ctx, ctx.devices[0])
        
        queue.wait(event)
        
        event2 = queue.marker()
        event2.add_callback(callback)
        
        self.assertEqual(event.status, Event.SUBMITTED)
        self.assertEqual(event2.status, Event.QUEUED)
        
        self.assertFalse(self.callback_called)
        event.complete()
        self.assertEqual(event.status, Event.COMPLETE)
        
        event2.wait()
        self.assertEqual(event2.status, Event.COMPLETE)
        
        event_is_set = self.py_event.wait(2)
        
        self.assertTrue(event_is_set, 'timed out waiting for callback')

        self.assertTrue(self.callback_called)
        
if __name__ == '__main__':
    unittest.main()