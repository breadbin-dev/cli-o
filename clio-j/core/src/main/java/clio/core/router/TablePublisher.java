package clio.core.router;

import java.util.*;

public class TablePublisher extends Publisher {

    private final List<Object> columns = new ArrayList<>();
    private final List<Object> menus = new ArrayList<>();

    public TablePublisher(RouterClient client, String function, int refreshMs) {
        super(client, function, "table", refreshMs);
    }

    public void addColumns(String... columns) {
        for (String column : columns)
            addColumn(column);
    }

    public void addColumns(List<?> columns) {
        this.columns.addAll(columns);
    }

    public void addColumn(String column) {
        addColumn(column, column);
    }

    public void addColumn(String column, String header) {
        columns.add(Map.of("field", column, "headerName", header));
    }

    public void addMenu(String name, String command) {
        menus.add(Map.of("name", name, "command", command));
    }

    public void addMenu(String name, String command, Map<String, List<String>> filter) {
        menus.add(Map.of("name", name, "command", command, "filter", filter));
    }

    public String publish(Map<String, ?> updates) {
        if (first) {
            var initial = new LinkedHashMap<String, Object>(updates);
            initial.put("__cols__", columns);
            if (!menus.isEmpty())
                initial.put("__menu__", menus);
            return super.publish(initial);
        } else {
            return super.publish(updates);
        }
    }
}
