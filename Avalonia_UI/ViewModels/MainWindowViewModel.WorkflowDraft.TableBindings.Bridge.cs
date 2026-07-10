using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private long workflowNodeTableBindingsDraftRevision;
    private long workflowNodeTableBindingsTableCatalogRevision;
    private string workflowNodeTableBindingsNodeCatalogHash = "unloaded";
    private string? workflowNodeTableBindingsRefreshKey;

    public WorkflowNodeTableBindingsViewModel WorkflowNodeTableBindings { get; private set; } = null!;

    private void InitializeWorkflowNodeTableBindings()
    {
        WorkflowNodeTableBindings = new WorkflowNodeTableBindingsViewModel(
            T,
            ApplyWorkflowNodeTableBindingsDraftAsync);
        RefreshWorkflowNodeTableBindingsFromDraft(force: true);
    }

    private void AdvanceWorkflowNodeTableBindingsDraftRevision()
    {
        workflowNodeTableBindingsDraftRevision++;
    }

    private void UpdateWorkflowNodeTableBindingsNodeCatalog(string? catalogHash)
    {
        workflowNodeTableBindingsNodeCatalogHash = string.IsNullOrWhiteSpace(catalogHash)
            ? $"local-{NodeDefinitions.Count}"
            : catalogHash;
        workflowNodeTableBindingsTableCatalogRevision++;
        RefreshWorkflowNodeTableBindingsFromDraft();
    }

    private void NotifyWorkflowNodeTableBindingsTableCatalogChanged()
    {
        workflowNodeTableBindingsTableCatalogRevision++;
        RefreshWorkflowNodeTableBindingsFromDraft();
    }

    private void RefreshWorkflowNodeTableBindingsFromDraft(bool force = false)
    {
        if (WorkflowNodeTableBindings is null)
        {
            return;
        }

        var selectedNode = SelectedWorkflowDefinitionNode;
        if (selectedNode is null || string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
        {
            workflowNodeTableBindingsRefreshKey = null;
            WorkflowNodeTableBindings.Clear();
            return;
        }

        var catalogHash = $"{workflowNodeTableBindingsNodeCatalogHash}|tables:{workflowNodeTableBindingsTableCatalogRevision}";
        var refreshKey = $"{workflowNodeTableBindingsDraftRevision}|{selectedNode.NodeInstanceId}|{catalogHash}";
        if (!force && string.Equals(
                workflowNodeTableBindingsRefreshKey,
                refreshKey,
                StringComparison.Ordinal))
        {
            return;
        }

        workflowNodeTableBindingsRefreshKey = refreshKey;
        var snapshot = workflowDefinitionDraftParseCache.GetSnapshot(
            WorkflowDefinitionDraftJson);
        if (snapshot is null)
        {
            WorkflowNodeTableBindings.Clear();
            return;
        }

        var definitions = NodeDefinitions.Select(ToNodeDefinitionDto).ToArray();
        var selectedDefinition = definitions.FirstOrDefault(definition =>
            definition.NodeType == selectedNode.NodeType &&
            definition.NodeVersion == selectedNode.NodeVersion);
        WorkflowNodeTableBindings.Load(
            WorkflowDefinitionDraftJson,
            workflowNodeTableBindingsDraftRevision.ToString(),
            snapshot,
            selectedNode.NodeInstanceId,
            selectedDefinition,
            definitions,
            catalogHash,
            TableRefs.Select(ToTableRefDto).ToArray(),
            workflowDefinitionDraftParseCache.GetNodeTableBindings(
                WorkflowDefinitionDraftJson,
                selectedNode.NodeInstanceId));
    }

    private async Task ApplyWorkflowNodeTableBindingsDraftAsync(string updatedDraftJson)
    {
        WorkflowDefinitionDraftJson = updatedDraftJson;
        await ValidateWorkflowDefinitionDraftAsync();
    }

    private static NodeDefinitionDto ToNodeDefinitionDto(
        NodeDefinitionListItemViewModel definition)
    {
        return new NodeDefinitionDto
        {
            NodeType = definition.NodeType,
            NodeVersion = definition.NodeVersion,
            DisplayName = definition.DisplayName,
            InputPorts = definition.InputPorts,
            OutputPorts = definition.OutputPorts,
            InputTableSlots = definition.InputTableSlots,
            OutputTableSlots = definition.OutputTableSlots,
            ExecutionMode = definition.ExecutionMode,
            DefaultTimeoutSeconds = definition.DefaultTimeoutSeconds,
            RetrySafe = definition.RetrySafe,
            UiVisibility = definition.UiVisibility,
        };
    }

    private static TableRefDto ToTableRefDto(TableRefListItemViewModel table)
    {
        return new TableRefDto
        {
            TableRefId = table.TableRefId,
            WorkflowRunId = table.WorkflowRunId,
            NodeRunId = table.NodeRunId,
            SourceNodeRunId = table.SourceNodeRunId,
            SourceNodeInstanceId = table.SourceNodeInstanceId,
            Role = table.Role,
            StorageKind = table.StorageKind,
            Scope = table.Scope,
            Mutability = table.Mutability,
            ProviderId = table.ProviderId,
            ResourceProfileId = table.ResourceProfileId,
            MountId = table.MountId,
            LogicalTableId = table.LogicalTableId,
            OutputSlot = table.OutputSlot,
            TableType = table.TableType,
            PreviewPersistence = table.PreviewPersistence,
            CanReadRows = table.CanReadRows,
            SupportsPagedRows = table.SupportsPagedRows,
            Version = table.Version,
            Capabilities = table.Capabilities,
            LifecycleStatus = table.LifecycleStatus,
            CreatedAt = table.CreatedAt,
        };
    }
}
