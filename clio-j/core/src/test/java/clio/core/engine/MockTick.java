package clio.core.engine;

import java.util.List;
import java.util.Map;

public record MockTick(long seq, Map<String, MockObj> mapInputs, List<Double> listInputs, String lastInput) {
}
