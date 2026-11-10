#!/usr/bin/env python3
"""Real DDS/action transport against a MOCK Nav2 server; does not move a robot.

Run in an isolated domain after colcon build:
ROS_DOMAIN_ID=73 python3 src/tb4_voice_navigation/test/check_ros_integration.py
"""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
loader = importlib.machinery.SourceFileLoader('voice_navigation', str(PACKAGE / 'scripts/voice_navigation_node'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class Harness(Node):
    def __init__(self):
        super().__init__('mock_nav2_lab7')
        self.mode, self.seen, self.statuses = 'success', [], []
        self.cancelled = 0
        self.publisher = self.create_publisher(String, 'voice_nav/text', 10)
        self.create_subscription(String, 'voice_nav/status', lambda msg: self.statuses.append(json.loads(msg.data)), 50)
        self.server = ActionServer(self, NavigateToPose, 'navigate_to_pose', self.execute,
                                   goal_callback=self.goal, cancel_callback=self.cancel,
                                   callback_group=ReentrantCallbackGroup())

    def goal(self, request):
        self.seen.append(request.pose)
        if self.mode == 'late_accept':
            time.sleep(.4)
        return GoalResponse.REJECT if self.mode == 'reject' else GoalResponse.ACCEPT

    def cancel(self, _):
        self.cancelled += 1
        return CancelResponse.ACCEPT

    def execute(self, handle):
        deadline = time.monotonic() + (5 if self.mode in ('hold', 'late_accept') else .15)
        while time.monotonic() < deadline:
            if handle.is_cancel_requested:
                handle.canceled()
                return NavigateToPose.Result()
            time.sleep(.01)
        if self.mode == 'abort':
            handle.abort()
        else:
            handle.succeed()
        return NavigateToPose.Result()


def main():
    rclpy.init(args=['--ros-args', '-p', 'use_sim_time:=false', '-p', 'goal_timeout:=0.8'])
    harness, consumer = Harness(), module.VoiceNavigation()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(harness)
    executor.add_node(consumer)
    outcomes = []

    def until(predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert predicate(), 'Timed out waiting for test condition'

    def send(text):
        harness.publisher.publish(String(data=text))

    def reset(mode='success'):
        assert not consumer.busy
        # Drain status messages from the preceding scenario before clearing evidence.
        for _ in range(10):
            executor.spin_once(timeout_sec=.01)
        harness.mode, harness.seen, harness.statuses, harness.cancelled = mode, [], [], 0

    def state(name):
        return any(x['state'] == name for x in harness.statuses)

    def record(name):
        outcomes.append(dict(test=name, passed=True, goal_count=len(harness.seen),
                             cancellations=harness.cancelled, states=[x['state'] for x in harness.statuses]))

    try:
        until(lambda: consumer.client.server_is_ready() and harness.publisher.get_subscription_count() > 0)
        for text, ids in [('Đi đến khu vực A', ['A']),
                          ('Di chuyển từ khu vực A đến khu vực B', ['A', 'B']),
                          ('Đi đến phòng thí nghiệm', ['B']),
                          ('Đi từ phòng A qua hành lang C rồi đến phòng B', ['A', 'C', 'B'])]:
            reset()
            send(text)
            until(lambda: state('completed'))
            assert len(harness.seen) == len(ids)
            for pose, rid in zip(harness.seen, ids):
                expected = consumer.catalog.regions[rid]['goal']
                assert pose.header.frame_id == 'map'
                assert abs(pose.pose.position.x - expected['x']) < 1e-8
                assert abs(pose.pose.position.y - expected['y']) < 1e-8
            record(text)
        for text in ['Đi từ A qua khu vực Z rồi đến B', 'Không đi đến A']:
            reset()
            send(text)
            until(lambda: state('invalid_command'))
            assert not harness.seen
            record(text)
        for mode, terminal in [('reject', 'rejected'), ('abort', 'failed')]:
            reset(mode)
            send('Đi từ A đến B')
            until(lambda: state(terminal))
            assert len(harness.seen) == 1 and not consumer.busy
            record(mode + '_stops_route')
        reset('hold')
        send('Đi từ A đến B')
        until(lambda: consumer.goal_handle is not None)
        send('Đi đến C')
        until(lambda: state('busy'))
        send('Dừng lại')
        until(lambda: state('stopped'))
        assert len(harness.seen) == 1 and harness.cancelled == 1
        record('busy_and_stop')
        reset('hold')
        send('Đi từ A đến B')
        until(lambda: state('stopped'))
        assert len(harness.seen) == 1 and harness.cancelled == 1
        assert any('Quá thời gian' in x['message'] for x in harness.statuses)
        record('timeout_cancels_route')
        reset('late_accept')
        send('Đi từ A đến B')
        until(lambda: len(harness.seen) == 1)
        send('Hủy lệnh')
        until(lambda: state('stopped'))
        assert len(harness.seen) == 1 and harness.cancelled == 1
        record('stop_before_acceptance')
    finally:
        executor.shutdown(timeout_sec=6)
        harness.server.destroy()
        harness.destroy_node()
        consumer.destroy_node()
        rclpy.shutdown()
    target = PACKAGE.parents[1] / 'docs/lab7/ros_integration.json'
    target.write_text(json.dumps({'server': 'MOCK NavigateToPose, no robot motion', 'tests': outcomes},
                                 indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'PASS: {len(outcomes)} ROS integration scenarios; evidence: {target}')


if __name__ == '__main__':
    main()
