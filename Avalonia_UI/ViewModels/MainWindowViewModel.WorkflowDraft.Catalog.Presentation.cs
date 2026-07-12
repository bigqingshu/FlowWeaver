namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasNodeDefinitionCatalogError =>
        !string.IsNullOrWhiteSpace(NodeDefinitionCatalogErrorMessage);

    public bool HasNodeDefinitions => NodeDefinitions.Count > 0;

    public bool HasNodeDefinitionCatalogEmptyState =>
        !IsLoadingNodeDefinitions && !HasNodeDefinitions;

    public string? RefreshNodeDefinitionsDisabledReasonText
    {
        get
        {
            if (IsLoadingNodeDefinitions)
            {
                return T("action.disabled.busy");
            }

            if (!CanUseEngineActions)
            {
                return T("action.disabled.engine_not_connected");
            }

            return null;
        }
    }

    public string NodeCatalogSectionText => T("node_catalog.section");

    public string NodeText => T("node_catalog.node");

    public string NodeCatalogEmptyStateText => T("node_catalog.empty_state");

    public string InputsText => T("node_catalog.inputs");

    public string OutputsText => T("node_catalog.outputs");

    public string NodeCatalogSourceText => T("node_catalog.source");

    public string ModeText => T("node_catalog.mode");

    public string TimeoutText => T("node_catalog.timeout");
}
