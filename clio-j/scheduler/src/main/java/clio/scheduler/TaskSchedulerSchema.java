package clio.scheduler;

import clio.core.ServiceStatus;
import clio.core.db.Databases;
import clio.core.Strings;
import clio.scheduler.tasks.TaskStatus;

import java.util.List;

public class TaskSchedulerSchema {
    public static void main(String[] args) {
        var classes = List.of(ServiceStatus.class, TaskStatus.class);

        var tables = new StringBuilder();
        for (var cls : classes)
            tables.append(Databases.tableForCls(cls));

        Strings.writeFile(tables.toString(), "scheduler/src/main/resources/scheduler_schema.sql");
    }
}
