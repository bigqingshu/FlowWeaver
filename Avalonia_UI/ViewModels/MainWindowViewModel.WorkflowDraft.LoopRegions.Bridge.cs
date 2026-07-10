using System.Collections.Generic;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public WorkflowLoopRegionsViewModel WorkflowLoopRegions { get; private set; } = null!;

    private void InitializeWorkflowLoopRegions()
    {
        WorkflowLoopRegions = new WorkflowLoopRegionsViewModel(
            T,
            ApplyWorkflowLoopRegionDraftAsync);
        RefreshWorkflowLoopRegionsFromDraft();
    }

    private void RefreshWorkflowLoopRegionsFromDraft()
    {
        if (WorkflowLoopRegions is null)
        {
            return;
        }

        var readResult = workflowDefinitionDraftParseCache.GetLoopRegions(
            WorkflowDefinitionDraftJson);
        WorkflowLoopRegions.Load(
            WorkflowDefinitionDraftJson,
            readResult,
            WorkflowDefinitionDraftStructure?.Nodes ??
                (IReadOnlyList<WorkflowDefinitionDraftNode>)[]);
    }

    private async Task ApplyWorkflowLoopRegionDraftAsync(string updatedDraftJson)
    {
        WorkflowDefinitionDraftJson = updatedDraftJson;
        await ValidateWorkflowDefinitionDraftAsync();
    }
}
