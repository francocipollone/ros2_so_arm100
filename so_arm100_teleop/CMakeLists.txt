cmake_minimum_required(VERSION 3.22)
project(so_arm100_teleop)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME}/)

install(PROGRAMS scripts/leader_teleop_node
        DESTINATION lib/${PROJECT_NAME})

ament_python_install_package(${PROJECT_NAME} SCRIPTS_DESTINATION
                             lib/${PROJECT_NAME})

ament_package()
