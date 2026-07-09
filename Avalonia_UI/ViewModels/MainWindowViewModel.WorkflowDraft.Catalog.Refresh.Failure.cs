using System.Collections.Generic;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyNodeDefinitionsRefreshFailure(
        ApiResponseEnvelope<List<NodeDefinitionDto>> response)
    {
        NodeDefinitionCatalogMessage = T("node_catalog.refresh_failed");
        NodeDefinitionCatalogErrorMessage = DescribeError(response);
        SelectedNewDraftNodeDefinition = null;
        NotifyNodeDefinitionCatalogPresentationStateChanged();
        RefreshSelectedNodeConfigDraftState();
    }
}
