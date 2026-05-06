package clio.scheduler.adapters;

import clio.core.db.JdbcAdapter;
import clio.scheduler.tasks.TaskResultState;
import clio.scheduler.tasks.TaskState;
import clio.scheduler.tasks.TaskStatus;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class TaskStatusJdbcAdapter extends JdbcAdapter<TaskStatus> {

    public TaskStatusJdbcAdapter() {
        super(TaskStatus.class);
    }

    @Override
    public void insert(TaskStatus obj, PreparedStatement stmt) throws SQLException {
        var i = 0;
        stmt.setTimestamp(++i, toTimestamp(obj.dttm()));
        stmt.setString(++i, obj.name());
        stmt.setString(++i, obj.state().toString());
        stmt.setTimestamp(++i, toTimestamp(obj.nextDttm()));
        stmt.setTimestamp(++i, toTimestamp(obj.previousDttm()));
        stmt.setString(++i, obj.previousResult().toString());
        stmt.setString(++i, obj.msg());
    }

    @Override
    public TaskStatus select(ResultSet result) throws SQLException {
        var i = 0;
        var dttm = fromTimestamp(result.getTimestamp(++i));
        var name = result.getString(++i);
        var state = TaskState.valueOf(result.getString(++i));
        var nextDttm = fromTimestamp(result.getTimestamp(++i));
        var previousDttm = fromTimestamp(result.getTimestamp(++i));
        var previousResult = TaskResultState.valueOf(result.getString(++i));
        var msg = result.getString(++i);
        return new TaskStatus(dttm, name, state, nextDttm, previousDttm, previousResult, msg);
    }
}
