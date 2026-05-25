package clio.core.adapters;

import clio.core.ServiceStatus;
import clio.core.db.JdbcAdapter;
import clio.core.db.JdbcResult;
import clio.core.db.JdbcStatement;

import java.sql.SQLException;

public class ServiceStatusJdbcAdapter extends JdbcAdapter<ServiceStatus> {
    public ServiceStatusJdbcAdapter() {
        super(ServiceStatus.class);
    }

    @Override
    public void insert(ServiceStatus obj, JdbcStatement stmt) throws SQLException {
        stmt.setDttm(obj.dttm());
        stmt.setString(obj.name());
        stmt.setBool(obj.running());
        stmt.setBool(obj.connected());
        stmt.setString(obj.msg());
    }

    @Override
    public ServiceStatus select(JdbcResult result) throws SQLException {
        return new ServiceStatus(
                result.getDttm(),
                result.getString(),
                result.getBool(),
                result.getBool(),
                result.getString()
        );
    }
}
