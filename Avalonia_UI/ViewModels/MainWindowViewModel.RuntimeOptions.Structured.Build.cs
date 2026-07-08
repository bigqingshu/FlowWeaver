using System.Collections.Generic;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            draft = new RuntimeOptionsDraft();
            errorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? string.Empty;
            return false;
        }

        return TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out draft,
            out errorMessage);
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        RuntimeOptionsDraft baseDraft,
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsDraft();
        if (!TryBuildRuntimeOptionsWorkflowDraft(
            out var workflowDraft,
            out errorMessage))
        {
            return false;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                baseDraft.NodeOverrides);
        if (SelectedRuntimeOptionsNode is not null)
        {
            if (!TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
                out var nodeOverride,
                out errorMessage))
            {
                return false;
            }

            nodeOverrides[SelectedRuntimeOptionsNode.NodeInstanceId] = nodeOverride;
        }

        draft = new RuntimeOptionsDraft
        {
            Version = RuntimeOptionsDefaults.Version,
            Workflow = workflowDraft,
            NodeOverrides = nodeOverrides,
        };
        return TryValidateRuntimeOptionsDraft(draft, out errorMessage);
    }

}
