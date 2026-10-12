# Mesh2HRTF-perf, modified 2026-10-12. Inherited EUPL-1.2 license.
CXX ?= g++
OPTIM ?= -O2
OPENMP_FLAGS ?= -fopenmp
EVALUATION_VELOCITY ?= 0
CPPFLAGS += -DNDEBUG -DMRADM_ENABLE_OMP -DNUMCALC_EVALUATION_VELOCITY=$(EVALUATION_VELOCITY)
CXXFLAGS += -std=c++11 $(OPTIM) $(OPENMP_FLAGS)

SOURCES = NC_3dFunctions.cpp NC_CommonFunctions.cpp NC_Input.cpp \
          NC_PostProcessing.cpp NC_Addresses.cpp NC_EquationSystem.cpp NC_Main.cpp
OBJECTS = $(SOURCES:.cpp=.o)
EXECUTABLE = ../bin/NumCalc

.PHONY: all clean
all: $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	mkdir -p $(@D)
	$(CXX) $(OBJECTS) $(LDFLAGS) $(OPENMP_FLAGS) $(LDLIBS) -o $@

%.o: %.cpp $(wildcard *.h) Makefile
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

clean:
	$(RM) $(OBJECTS) $(EXECUTABLE)
