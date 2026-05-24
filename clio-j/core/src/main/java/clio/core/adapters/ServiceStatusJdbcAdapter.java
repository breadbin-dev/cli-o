package clio.core.adapters;

import clio.core.ServiceStatus;
import clio.core.db.JdbcAdapter;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class ServiceStatusJdbcAdapter extends JdbcAdapter<ServiceStatus> {
    public ServiceStatusJdbcAdapter() {
        super(ServiceStatus.class);
    }

    @Override
    public void insert(ServiceStatus obj, PreparedStatement stmt) throws SQLException {
        var i = 0;
        stmt.setTimestamp(++i, toTimestamp(obj.dttm()));
        stmt.setString(++i, obj.name());
        stmt.setBoolean(++i, obj.running());
        stmt.setBoolean(++i, obj.connected());
        stmt.setString(++i, obj.msg());
    }

    @Override
    public ServiceStatus select(ResultSet result) throws SQLException {
        var i = 0;
        var dttm = fromTimestamp(result.getTimestamp(++i));
        var name = result.getString(++i);
        var running = result.getBoolean(++i);
        var connected = result.getBoolean(++i);
        var msg = result.getString(++i);
        return new ServiceStatus(dttm, name, running, connected, msg);
    }
}
