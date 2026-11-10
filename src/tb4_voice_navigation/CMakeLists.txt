cmake_minimum_required(VERSION 3.8)
project(tb4_voice_navigation)
find_package(ament_cmake REQUIRED)
install(DIRECTORY launch config maps DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE)
install(PROGRAMS scripts/segment_map scripts/voice_navigation_node scripts/speech_recognition_node
  DESTINATION lib/${PROJECT_NAME})
install(FILES scripts/semantic_map.py scripts/voice_core.py DESTINATION lib/${PROJECT_NAME})
install(FILES LICENSE README.md DESTINATION share/${PROJECT_NAME})
if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(voice_core test/test_core.py TIMEOUT 60)
endif()
ament_package()
