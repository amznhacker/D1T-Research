Download d1-sdk and unzip it 
create a folder called build. 
```
mkdir build 
cd build
cmake ..
make

```

When the robot arm is plugged it takes 10 seconds before we can ping it, then executing anything like /.arm_zero_control takes over 1 minute and 10 seconds 

when /.arm_zero_control is executed the zero pose remains even after disconnected from the computer. 
