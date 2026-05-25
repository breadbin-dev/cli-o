package clio.scheduler.adapters;

import clio.core.db.JdbcAdapter;
import clio.core.db.JdbcResult;
import clio.core.db.JdbcStatement;
import clio.scheduler.tasks.TaskResultState;
import clio.scheduler.tasks.TaskState;
import clio.scheduler.tasks.TaskStatus;

import java.sql.SQLException;

public class TaskStatusJdbcAdapter extends JdbcAdapter<TaskStatus> {

    public TaskStatusJdbcAdapter() {
        super(TaskStatus.class);
    }

    @Override
    public void insert(TaskStatus obj, JdbcStatement stmt) throws SQLException {
        stmt.setDttm(obj.dttm());
        stmt.setString(obj.name());
        stmt.setString(obj.state().toString());
        stmt.setDttm(obj.nextDttm());
        stmt.setDttm(obj.previousDttm());
        stmt.setString(obj.previousResult().toString());
        stmt.setString(obj.msg());
    }

    @Override
    public TaskStatus select(JdbcResult result) throws SQLException {
        return new TaskStatus(
                result.getDttm(),
                result.getString(),
                TaskState.valueOf(result.getString()),
                result.getDttm(),
                result.getDttm(),
                TaskResultState.valueOf(result.getString()),
                result.getString()
        );
    }
}
