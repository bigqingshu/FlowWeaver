using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public sealed class NodeTableInputSourceOptionViewModel
{
    public NodeTableInputSourceOptionViewModel(
        NodeTableInputBindingDraft binding,
        string displayText)
    {
        Binding = binding;
        DisplayText = displayText;
    }

    public NodeTableInputBindingDraft Binding { get; }

    public string DisplayText { get; }
}

public sealed partial class NodeTableInputBindingViewModel : ViewModelBase
{
    private readonly Action<NodeTableInputBindingViewModel> selectionChanged;
    private bool isLoading;

    public NodeTableInputBindingViewModel(
        NodeTableInputSlotDto slot,
        IReadOnlyList<NodeTableInputBindingCandidate> candidates,
        NodeTableInputBindingDraft? draft,
        Func<string, string> translate,
        Action<NodeTableInputBindingViewModel> selectionChanged)
    {
        this.selectionChanged = selectionChanged;
        SlotName = slot.Name;
        SlotTitleText = $"{translate("workflow.table_bindings.input_slot")} ({slot.Name})";
        Description = slot.Description ?? string.Empty;
        RequiredText = slot.Required
            ? translate("workflow.table_bindings.required")
            : translate("workflow.table_bindings.optional");
        IsRequired = slot.Required;
        AllowedStorageKinds = slot.AllowedStorageKinds;

        Sources.Add(new NodeTableInputSourceOptionViewModel(
            new NodeTableInputBindingDraft { Slot = slot.Name },
            translate("workflow.table_bindings.current_table")));
        foreach (var candidate in candidates.Where(candidate =>
            IsStorageAllowed(candidate.StorageKind, slot.AllowedStorageKinds)))
        {
            Sources.Add(new NodeTableInputSourceOptionViewModel(
                new NodeTableInputBindingDraft
                {
                    Slot = slot.Name,
                    Type = NodeTableInputBindingDraft.UpstreamTableSourceType,
                    SourceNodeInstanceId = candidate.SourceNodeInstanceId,
                    OutputSlot = candidate.OutputSlot,
                    OutputRole = candidate.OutputRole,
                    StorageKind = candidate.StorageKind,
                    LogicalTableId = candidate.LogicalTableId,
                },
                FormatCandidate(candidate)));
        }

        isLoading = true;
        SelectedSource = FindMatchingSource(draft)
            ?? DefaultSource(slot.DefaultSource);
        isLoading = false;
    }

    public string SlotName { get; }

    public string SlotTitleText { get; }

    public string Description { get; }

    public string RequiredText { get; }

    public bool IsRequired { get; }

    public string[] AllowedStorageKinds { get; }

    public ObservableCollection<NodeTableInputSourceOptionViewModel> Sources { get; } = new();

    [ObservableProperty]
    private NodeTableInputSourceOptionViewModel? selectedSource;

    public bool HasSelection => SelectedSource is not null;

    public NodeTableInputBindingDraft? BuildDraft()
    {
        var source = SelectedSource;
        return source is null
            ? null
            : source.Binding with { Slot = SlotName };
    }

    partial void OnSelectedSourceChanged(NodeTableInputSourceOptionViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelection));
        if (!isLoading)
        {
            selectionChanged(this);
        }
    }

    private NodeTableInputSourceOptionViewModel? FindMatchingSource(
        NodeTableInputBindingDraft? draft)
    {
        return draft is null
            ? null
            : Sources.FirstOrDefault(option => Matches(option.Binding, draft));
    }

    private NodeTableInputSourceOptionViewModel? DefaultSource(string? defaultSource)
    {
        if (string.Equals(defaultSource, "upstream_current", StringComparison.Ordinal))
        {
            return Sources.FirstOrDefault(source => source.Binding.IsUpstreamTable)
                ?? Sources.FirstOrDefault();
        }

        return Sources.FirstOrDefault();
    }

    private static bool Matches(
        NodeTableInputBindingDraft candidate,
        NodeTableInputBindingDraft draft)
    {
        if (!string.Equals(candidate.Type, draft.Type, StringComparison.Ordinal))
        {
            return false;
        }

        if (draft.IsCurrent)
        {
            return candidate.IsCurrent;
        }

        return string.Equals(
                candidate.SourceNodeInstanceId,
                draft.SourceNodeInstanceId,
                StringComparison.Ordinal) &&
            MatchesOptional(candidate.OutputSlot, draft.OutputSlot) &&
            MatchesOptional(candidate.OutputRole, draft.OutputRole) &&
            MatchesOptional(candidate.StorageKind, draft.StorageKind) &&
            MatchesOptional(candidate.LogicalTableId, draft.LogicalTableId);
    }

    private static bool MatchesOptional(string? candidate, string? expected)
    {
        return string.IsNullOrWhiteSpace(expected) ||
            string.Equals(candidate, expected, StringComparison.Ordinal);
    }

    private static bool IsStorageAllowed(
        string? storageKind,
        IReadOnlyCollection<string> allowedStorageKinds)
    {
        return string.IsNullOrWhiteSpace(storageKind) ||
            allowedStorageKinds.Count == 0 ||
            allowedStorageKinds.Contains(storageKind, StringComparer.Ordinal);
    }

    private static string FormatCandidate(NodeTableInputBindingCandidate candidate)
    {
        var source = string.IsNullOrWhiteSpace(candidate.SourceNodeDisplayName)
            ? candidate.SourceNodeInstanceId
            : $"{candidate.SourceNodeDisplayName} [{candidate.SourceNodeInstanceId}]";
        var slot = string.Equals(
                candidate.OutputSlotDisplayName,
                candidate.OutputSlot,
                StringComparison.Ordinal)
            ? candidate.OutputSlot
            : $"{candidate.OutputSlotDisplayName} ({candidate.OutputSlot})";
        var identity = string.IsNullOrWhiteSpace(candidate.LogicalTableId)
            ? candidate.StorageKind ?? candidate.OutputRole
            : $"{candidate.StorageKind ?? candidate.OutputRole}: {candidate.LogicalTableId}";
        return $"{source} | {slot} | {identity}";
    }
}
