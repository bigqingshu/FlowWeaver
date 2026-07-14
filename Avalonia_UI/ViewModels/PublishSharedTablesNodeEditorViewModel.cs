using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
using System.Linq;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class PublishSharedTablesNodeEditorViewModel : ViewModelBase,
    INodeSpecializedEditorViewModel
{
    private readonly ILocalizationService _localizationService;
    private readonly int _connectedInputCount;

    private PublishSharedTablesNodeEditorViewModel(
        NodeSpecializedEditorContext context,
        NodeConfigEditableFieldInputViewModel shareNameField,
        NodeConfigEditableFieldInputViewModel exportNamesField,
        NodeConfigEditableFieldInputViewModel? retentionSecondsField)
    {
        _localizationService = context.LocalizationService;
        NodeType = context.Node.NodeType;
        ShareNameField = shareNameField;
        ExportNamesField = exportNamesField;
        RetentionSecondsField = retentionSecondsField;

        var connections = context.Connections
            .Where(connection => string.Equals(
                connection.TargetNodeId,
                context.Node.NodeInstanceId,
                StringComparison.Ordinal))
            .ToArray();
        _connectedInputCount = connections.Length;
        var existingNames = exportNamesField.StringArrayItems
            .Select(item => item.Value)
            .ToArray();
        var rowCount = Math.Max(connections.Length, existingNames.Length);
        InputMappings = new ObservableCollection<PublishSharedTableInputMappingViewModel>(
            Enumerable.Range(0, rowCount)
                .Select(index => new PublishSharedTableInputMappingViewModel(
                    index + 1,
                    index < connections.Length ? connections[index] : null,
                    index < existingNames.Length ? existingNames[index] : string.Empty,
                    _localizationService)));
        foreach (var mapping in InputMappings)
        {
            mapping.PropertyChanged += OnInputMappingPropertyChanged;
        }
    }

    public static PublishSharedTablesNodeEditorViewModel? TryCreate(
        NodeSpecializedEditorContext context)
    {
        var shareNameField = FindField(context.Fields, "share_name");
        var exportNamesField = FindField(context.Fields, "export_names");
        if (shareNameField is null
            || exportNamesField?.IsStringArrayInput != true)
        {
            return null;
        }

        return new PublishSharedTablesNodeEditorViewModel(
            context,
            shareNameField,
            exportNamesField,
            FindField(context.Fields, "retention_seconds"));
    }

    public string NodeType { get; }

    public event EventHandler? ConfigChanged;

    public NodeConfigEditableFieldInputViewModel ShareNameField { get; }

    public NodeConfigEditableFieldInputViewModel ExportNamesField { get; }

    public NodeConfigEditableFieldInputViewModel? RetentionSecondsField { get; }

    public bool HasRetentionSecondsField => RetentionSecondsField is not null;

    public ObservableCollection<PublishSharedTableInputMappingViewModel> InputMappings { get; }

    public string ShareNameText =>
        _localizationService.GetString("node_config.shared.share_name");

    public string InputsText =>
        _localizationService.GetString("node_config.shared.publish.inputs");

    public string ExportNameText =>
        _localizationService.GetString("node_config.shared.publish.export_name");

    public string RetentionSecondsText =>
        _localizationService.GetString("node_config.shared.publish.retention_seconds");

    public bool TryPrepareApply(out string errorMessage)
    {
        if (string.IsNullOrWhiteSpace(ShareNameField.InputValue))
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.share_name_required");
            return false;
        }

        if (_connectedInputCount == 0)
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.publish_input_required");
            return false;
        }

        if (InputMappings.Count != _connectedInputCount)
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.export_count_mismatch");
            return false;
        }

        var exportNames = InputMappings
            .Select(mapping => mapping.ExportName)
            .ToArray();
        var emptyIndex = Array.FindIndex(exportNames, string.IsNullOrWhiteSpace);
        if (emptyIndex >= 0)
        {
            errorMessage = _localizationService.Format(
                "format.node_config.shared.error.export_name_required",
                emptyIndex + 1);
            return false;
        }

        if (exportNames.Distinct(StringComparer.Ordinal).Count() != exportNames.Length)
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.export_names_unique");
            return false;
        }

        if (RetentionSecondsField?.HasInputValue == true
            && (!long.TryParse(
                RetentionSecondsField.InputValue,
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out var retentionSeconds)
                || retentionSeconds <= 0))
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.retention_positive");
            return false;
        }

        ExportNamesField.ReplaceStringArrayValues(
            exportNames,
            hasInputValue: true);
        errorMessage = string.Empty;
        return true;
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(ShareNameText));
        OnPropertyChanged(nameof(InputsText));
        OnPropertyChanged(nameof(ExportNameText));
        OnPropertyChanged(nameof(RetentionSecondsText));
        foreach (var mapping in InputMappings)
        {
            mapping.RefreshLocalizedText();
        }
    }

    public void AcceptChanges()
    {
    }

    public void Dispose()
    {
        foreach (var mapping in InputMappings)
        {
            mapping.PropertyChanged -= OnInputMappingPropertyChanged;
        }
    }

    private void OnInputMappingPropertyChanged(
        object? sender,
        PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(PublishSharedTableInputMappingViewModel.ExportName))
        {
            ConfigChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    private static NodeConfigEditableFieldInputViewModel? FindField(
        IReadOnlyList<NodeConfigEditableFieldInputViewModel> fields,
        string name)
    {
        return fields.FirstOrDefault(
            field => string.Equals(field.Name, name, StringComparison.Ordinal));
    }
}
