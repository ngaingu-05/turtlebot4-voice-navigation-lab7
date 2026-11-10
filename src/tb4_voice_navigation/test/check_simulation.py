#!/usr/bin/env python3
"""SIMULATION ONLY: initialize from Gazebo truth, then exercise real Nav2.

Start Depot, AMCL/Nav2 and voice_navigation_node first, all in the same domain.
This sends TEXT commands and does not validate speech recognition.
"""
import json
import math
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseWithCovarianceStamped
from irobot_create_msgs.msg import DockStatus, HazardDetectionVector
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
from voice_core import RegionCatalog


def main():
    rclpy.init()
    node = Node('lab7_simulation_check')
    node.set_parameters([Parameter('use_sim_time', value=True)])
    catalog = RegionCatalog.load(PACKAGE / 'maps/regions.yaml')
    latest, states, poses = {}, [], []
    bump_events = 0
    hazard_messages = 0

    def remember(key, msg):
        latest[key] = msg
        if key == 'truth':
            p = msg.pose.pose.position
            poses.append(dict(t=node.get_clock().now().nanoseconds * 1e-9, x=p.x, y=p.y))

    def hazard(msg):
        nonlocal bump_events, hazard_messages
        hazard_messages += 1
        bump_events += sum(h.type == 1 for h in msg.detections)  # HazardDetection.BUMP

    for key, topic, kind in [('truth', 'sim_ground_truth_pose', Odometry),
                             ('amcl', 'amcl_pose', PoseWithCovarianceStamped),
                             ('scan', 'scan', LaserScan), ('dock', 'dock_status', DockStatus)]:
        node.create_subscription(kind, topic, lambda msg, key=key: remember(key, msg), qos_profile_sensor_data)
    node.create_subscription(HazardDetectionVector, 'hazard_detection', hazard, qos_profile_sensor_data)
    node.create_subscription(String, 'voice_nav/status', lambda msg: states.append(json.loads(msg.data)), 50)
    command = node.create_publisher(String, 'voice_nav/text', 10)
    initial = node.create_publisher(PoseWithCovarianceStamped, 'initialpose', 10)

    def wait(predicate, seconds=40):
        deadline = time.monotonic() + seconds
        while not predicate():
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Wait timed out; topics={list(latest)}, statuses={states[-3:]}')
            rclpy.spin_once(node, timeout_sec=.1)

    results = []
    output = dict(input='TEXT via ROS topic, not speech', environment='Jazzy / Gazebo Depot',
                  date='2026-11-10', initial_pose_source='Gazebo truth (simulation only)', results=results)
    try:
        wait(lambda: all(key in latest for key in ('truth', 'scan', 'dock')))
        if latest['dock'].is_docked:
            raise RuntimeError('Undock first, then rerun this simulation-only check')
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.pose.pose = latest['truth'].pose.pose
        msg.pose.pose.position.z = 0.
        msg.pose.covariance[0], msg.pose.covariance[7], msg.pose.covariance[35] = .04, .04, .02
        end = time.monotonic() + 5
        next_publish = 0.
        while time.monotonic() < end:
            if time.monotonic() >= next_publish:
                msg.header.stamp = node.get_clock().now().to_msg()
                initial.publish(msg)
                next_publish = time.monotonic() + .5
            rclpy.spin_once(node, timeout_sec=.1)
        wait(lambda: 'amcl' in latest)
        a, t = latest['amcl'].pose.pose.position, latest['truth'].pose.pose.position
        output['initial_localization_error_m'] = math.hypot(a.x - t.x, a.y - t.y)
        if output['initial_localization_error_m'] > .5:
            raise RuntimeError('AMCL differs from truth by >0.5 m')
        wait(lambda: command.get_subscription_count() > 0)
        # Wait for planner activation after map->odom becomes available.
        from rclpy.action import ActionClient
        from nav2_msgs.action import NavigateToPose
        from lifecycle_msgs.srv import GetState
        for name in ('amcl', 'planner_server', 'controller_server', 'bt_navigator'):
            lifecycle = node.create_client(GetState, name + '/get_state')
            deadline = time.monotonic() + 60
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'{name} did not become active')
                if not lifecycle.wait_for_service(timeout_sec=.2):
                    continue
                future = lifecycle.call_async(GetState.Request())
                wait(future.done, seconds=5)
                if future.result().current_state.id == 3:
                    break
                rclpy.spin_once(node, timeout_sec=.2)
            node.destroy_client(lifecycle)
        client = ActionClient(node, NavigateToPose, 'navigate_to_pose')
        wait(client.server_is_ready)
        for text, expected in [('Đi đến khu vực A', ['A']),
                               ('Di chuyển từ khu vực A đến khu vực B', ['A', 'B']),
                               ('Đi đến hành lang', ['C'])]:
            start = len(states)
            started = time.monotonic()
            command.publish(String(data=text))
            wait(lambda: any(s['state'] in ('completed', 'failed', 'rejected', 'unavailable', 'stopped')
                             for s in states[start:]), seconds=400)
            subset = states[start:]
            reached = [s['route'][s['index']] for s in subset if s['state'] == 'arrived']
            goal = catalog.regions[expected[-1]]['goal']
            p = latest['truth'].pose.pose.position
            result = dict(command=text, expected=expected, arrived=reached,
                          terminal=subset[-1]['state'], duration_s=time.monotonic() - started,
                          final_truth={'x': p.x, 'y': p.y},
                          final_error_m=math.hypot(p.x - goal['x'], p.y - goal['y']))
            result['passed'] = reached == expected and result['terminal'] == 'completed' and result['final_error_m'] < .5
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if not result['passed']:
                raise RuntimeError('Navigation case failed')
        start = len(states)
        command.publish(String(data='Đi đến khu vực Z'))
        wait(lambda: any(s['state'] == 'invalid_command' for s in states[start:]))
        output['unknown_region_rejected'] = True
        output['passed'] = True
    except Exception as exc:
        output['passed'], output['error'] = False, str(exc)
        command.publish(String(data='Dừng lại'))
        raise
    finally:
        output.update(hazard_messages=hazard_messages, bump_events=bump_events, states=states, poses=poses)
        target = PACKAGE.parents[1] / 'docs/lab7/simulation.json'
        target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
