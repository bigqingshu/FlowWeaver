using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public sealed record NodeTableOutputTargetKindOptionViewModel(
    string Value,
    string DisplayText);

public sealed record NodeTableExistingOutputOptionViewModel(
    NodeTableExistingOutputTargetCandidate Candidate,
    string DisplayText);

public sealed partial class NodeTableOutputTargetViewModel : ViewModelBase
{
    private readonly Action targetChanged;
    private bool isLoading;

    public NodeTableOutputTargetViewModel(
        NodeTableOutputSlotDto slot,
        IReadOnlyList<NodeTableExistingOutputTargetCandidate> existingTargets,
        NodeTableOutputTargetDraft? draft,
        Func<string, string> translate,
        Action targetChanged)
    {
        this.targetChanged = targetChanged;
        SlotName = slot.Name;
        SlotTitleText = $"{translate("workflow.table_bindings.output_slot")} ({slot.Name})";
        Description = slot.Description ?? string.Empty;
        TableNameText = translate("workflow.table_bindings.table_name");
        AddTargetKinds(slot, translate);
        AddExistingTargets(existingTargets);

        isLoading = true;
        LoadDraft(draft, slot.DefaultRole);
        isLoading = false;
        NotifyTargetStateChanged();
    }

    public string SlotName { get; }

    public string SlotTitleText { get; }

    public string Description { get; }

    public string TableNameText { get; }

    public ObservableCollection<NodeTableOutputTargetKindOptionViewModel> TargetKinds { get; } = new();

    public ObservableCollection<NodeTableExistingOutputOptionViewModel> ExistingTargets { get; } = new();

    [ObservableProperty]
    private NodeTableOutputTargetKindOptionViewModel? selectedTargetKind;

    [ObservableProperty]
    private NodeTableExistingOutputOptionViewModel? selectedExistingTarget;

    [ObservableProperty]
    private string logicalTableId = string.Empty;

    public bool IsCurrentTarget => SelectedTargetKind?.Value ==
        NodeTableOutputTargetDraft.CurrentTargetKind;

    public bool IsNewTarget => SelectedTargetKind?.Value is
        NodeTableOutputTargetDraft.NewMemoryTargetKind or
        NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind;

    public bool IsExistingTarget => SelectedTargetKind?.Value is
        NodeTableOutputTargetDraft.ExistingMemoryTargetKind or
        NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind;

    public bool IsValid => BuildDraft() is not null;

    public NodeTableOutputTargetDraft? BuildDraft()
    {
        var targetKind = SelectedTargetKind?.Value;
        if (targetKind is null)
        {
            return null;
        }

        if (targetKind == NodeTableOutputTargetDraft.CurrentTargetKind)
        {
            return new NodeTableOutputTargetDraft
            {
                Slot = SlotName,
                TargetKind = targetKind,
            };
        }

        var logicalId = IsExistingTarget
            ? SelectedExistingTarget?.Candidate.LogicalTableId
            : LogicalTableId?.Trim();
        if (string.IsNullOrWhiteSpace(logicalId))
        {
            return null;
        }

        return new NodeTableOutputTargetDraft
        {
            Slot = SlotName,
            TargetKind = targetKind,
            LogicalTableId = logicalId,
        };
    }

    public bool TryApplyInputSuggestion(NodeTableInputBindingDraft input)
    {
        if (input.IsCurrent)
        {
            return SelectTargetKind(NodeTableOutputTargetDraft.CurrentTargetKind);
        }

        if (string.IsNullOrWhiteSpace(input.StorageKind) ||
            string.IsNullOrWhiteSpace(input.LogicalTableId))
        {
            return false;
        }

        var targetKind = input.StorageKind switch
        {
            "MEMORY" => NodeTableOutputTargetDraft.ExistingMemoryTargetKind,
            "RUNTIME_SQL" => NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind,
            _ => null,
        };
        var existing = ExistingTargets.FirstOrDefault(option =>
            string.Equals(
                option.Candidate.StorageKind,
                input.StorageKind,
                StringComparison.Ordinal) &&
            string.Equals(
                option.Candidate.LogicalTableId,
                input.LogicalTableId,
                StringComparison.Ordinal));
        if (targetKind is null || existing is null || !SelectTargetKind(targetKind))
        {
            return false;
        }

        SelectedExistingTarget = existing;
        return true;
    }

    partial void OnSelectedTargetKindChanged(NodeTableOutputTargetKindOptionViewModel? value)
    {
        if (value?.Value == NodeTableOutputTargetDraft.CurrentTargetKind)
        {
            LogicalTableId = string.Empty;
            SelectedExistingTarget = null;
        }
        else if (value?.Value is
            NodeTableOutputTargetDraft.ExistingMemoryTargetKind or
            NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind)
        {
            var storageKind = value.Value == NodeTableOutputTargetDraft.ExistingMemoryTargetKind
                ? "MEMORY"
                : "RUNTIME_SQL";
            SelectedExistingTarget = ExistingTargets.FirstOrDefault(option =>
                option.Candidate.StorageKind == storageKind);
        }
        else
        {
            SelectedExistingTarget = null;
        }

        NotifyTargetStateChanged();
        NotifyChanged();
    }

    partial void OnSelectedExistingTargetChanged(NodeTableExistingOutputOptionViewModel? value)
    {
        if (value is not null)
        {
            LogicalTableId = value.Candidate.LogicalTableId;
        }

        NotifyTargetStateChanged();
        NotifyChanged();
    }

    partial void OnLogicalTableIdChanged(string value)
    {
        OnPropertyChanged(nameof(IsValid));
        NotifyChanged();
    }

    private void LoadDraft(NodeTableOutputTargetDraft? draft, string defaultRole)
    {
        var targetKind = draft?.TargetKind;
        if (targetKind is null && string.Equals(defaultRole, "CURRENT", StringComparison.Ordinal))
        {
            targetKind = NodeTableOutputTargetDraft.CurrentTargetKind;
        }

        SelectedTargetKind = TargetKinds.FirstOrDefault(option => option.Value == targetKind)
            ?? TargetKinds.FirstOrDefault();
        LogicalTableId = draft?.LogicalTableId ?? string.Empty;
        if (draft?.IsExistingTarget == true)
        {
            SelectedExistingTarget = ExistingTargets.FirstOrDefault(option =>
                string.Equals(
                    option.Candidate.StorageKind,
                    draft.StorageKind,
                    StringComparison.Ordinal) &&
                string.Equals(
                    option.Candidate.LogicalTableId,
                    draft.LogicalTableId,
                    StringComparison.Ordinal));
        }
    }

    private bool SelectTargetKind(string targetKind)
    {
        var option = TargetKinds.FirstOrDefault(item => item.Value == targetKind);
        if (option is null)
        {
            return false;
        }

        SelectedTargetKind = option;
        return true;
    }

    private void AddTargetKinds(
        NodeTableOutputSlotDto slot,
        Func<string, string> translate)
    {
        AddTargetKind(slot.AllowCurrent, NodeTableOutputTargetDraft.CurrentTargetKind, "current", translate);
        AddTargetKind(slot.AllowNewMemory, NodeTableOutputTargetDraft.NewMemoryTargetKind, "new_memory", translate);
        AddTargetKind(slot.AllowNewRuntimeSql, NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind, "new_runtime_sql", translate);
        AddTargetKind(slot.AllowExistingMemory, NodeTableOutputTargetDraft.ExistingMemoryTargetKind, "existing_memory", translate);
        AddTargetKind(slot.AllowExistingRuntimeSql, NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind, "existing_runtime_sql", translate);
    }

    private void AddTargetKind(
        bool allowed,
        string value,
        string localizationSuffix,
        Func<string, string> translate)
    {
        if (allowed)
        {
            TargetKinds.Add(new NodeTableOutputTargetKindOptionViewModel(
                value,
                $"{translate($"workflow.table_bindings.target.{localizationSuffix}")} ({value})"));
        }
    }

    private void AddExistingTargets(
        IReadOnlyList<NodeTableExistingOutputTargetCandidate> existingTargets)
    {
        foreach (var candidate in existingTargets.Where(candidate =>
            candidate.Role == "AUXILIARY" &&
            candidate.StorageKind is "MEMORY" or "RUNTIME_SQL"))
        {
            ExistingTargets.Add(new NodeTableExistingOutputOptionViewModel(
                candidate,
                $"{candidate.StorageKind}: {candidate.LogicalTableId}"));
        }
    }

    private void NotifyTargetStateChanged()
    {
        OnPropertyChanged(nameof(IsCurrentTarget));
        OnPropertyChanged(nameof(IsNewTarget));
        OnPropertyChanged(nameof(IsExistingTarget));
        OnPropertyChanged(nameof(IsValid));
    }

    private void NotifyChanged()
    {
        if (!isLoading)
        {
            targetChanged();
        }
    }
}
