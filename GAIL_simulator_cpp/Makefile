# Simple Makefile for quick builds

CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O3
INCLUDES = -Isrc
LIBS = -lyaml-cpp -lpthread

# 简单的源文件收集
SRCDIR = src
SOURCES = $(shell find $(SRCDIR) -name "*.cpp")
OBJECTS = $(SOURCES:.cpp=.o)
TARGET = gail_simulator

.PHONY: all clean debug

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(OBJECTS) -o $@ $(LIBS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

debug: CXXFLAGS = -std=c++17 -Wall -Wextra -g -DDEBUG
debug: $(TARGET)

clean:
	rm -f $(OBJECTS) $(TARGET)

install: $(TARGET)
	cp $(TARGET) /usr/local/bin/

# 显示帮助
help:
	@echo "Available targets:"
	@echo "  all     - Build the project (default)"
	@echo "  debug   - Build with debug symbols"
	@echo "  clean   - Remove build artifacts"
	@echo "  install - Install to /usr/local/bin"
	@echo "  help    - Show this help"
