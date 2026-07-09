namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string ConnectionsSectionText => T("definition.connections");

    public string ShowConnectionsText => IsWorkflowConnectionsAdvancedVisible
        ? T("definition.hide_connections")
        : T("definition.show_connections");

    public string AddConnectionText => T("definition.add_connection");

    public string DeleteConnectionText => T("definition.delete_connection");

    public string ConnectionIdText => T("definition.connection_id");

    public string SourceNodeText => T("definition.source_node");

    public string SourcePortText => T("definition.source_port");

    public string TargetNodeText => T("definition.target_node");

    public string TargetPortText => T("definition.target_port");
}
