using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class SqlMappingTableNodeEditorViewModel : ViewModelBase,
    INodeSpecializedEditorViewModel
{
    private const string TableMode = "table";
    private const string AllTablesMode = "all_tables";
    private const string QueryMode = "query";

    private readonly ILocalizationService _localizationService;
    private readonly ISqliteTableCatalogService _catalogService;
    private readonly ISqliteDatabaseFileService _fileService;
    private readonly CancellationToken _lifetimeToken;
    private readonly string _originalTableName;
    private readonly string _originalQuery;
    private CancellationTokenSource? _requestCts;
    private bool _disposed;
    private bool _rebuildingOptions;

    private SqlMappingTableNodeEditorViewModel(
        NodeSpecializedEditorContext context,
        NodeConfigEditableFieldInputViewModel sourceModeField,
        NodeConfigEditableFieldInputViewModel databasePathField,
        NodeConfigEditableFieldInputViewModel tableNameField,
        NodeConfigEditableFieldInputViewModel queryField,
        NodeConfigEditableFieldInputViewModel logicalTableIdField,
        NodeConfigEditableFieldInputViewModel? schemaField)
    {
        _localizationService = context.LocalizationService;
        _catalogService = context.SqliteTableCatalogService!;
        _fileService = context.SqliteDatabaseFileService!;
        _lifetimeToken = context.LifetimeToken;
        NodeType = context.Node.NodeType;
        SourceModeField = sourceModeField;
        DatabasePathField = databasePathField;
        TableNameField = tableNameField;
        QueryField = queryField;
        LogicalTableIdField = logicalTableIdField;
        SchemaField = schemaField;

        DatabasePath = databasePathField.HasInputValue
            ? databasePathField.InputValue
            : string.Empty;
        _originalTableName = tableNameField.HasInputValue
            ? tableNameField.InputValue
            : string.Empty;
        _originalQuery = queryField.HasInputValue
            ? queryField.InputValue
            : string.Empty;
        SqlQuery = _originalQuery;
        LogicalTableId = logicalTableIdField.HasInputValue
            ? logicalTableIdField.InputValue
            : string.Empty;

        SourceMode = ResolveInitialMode(sourceModeField, tableNameField, queryField);
        RebuildTableOptions(
            [],
            _originalTableName,
            includeMissingSelection: true);
    }

    public static SqlMappingTableNodeEditorViewModel? TryCreate(
        NodeSpecializedEditorContext context)
    {
        var sourceModeField = FindField(context.Fields, "source_mode");
        var databasePathField = FindField(context.Fields, "database_path");
        var tableNameField = FindField(context.Fields, "table_name");
        var queryField = FindField(context.Fields, "query");
        var logicalTableIdField = FindField(context.Fields, "logical_table_id");
        if (sourceModeField is null
            || databasePathField is null
            || tableNameField is null
            || queryField is null
            || logicalTableIdField is null
            || context.SqliteTableCatalogService is null
            || context.SqliteDatabaseFileService is null)
        {
            return null;
        }

        return new SqlMappingTableNodeEditorViewModel(
            context,
            sourceModeField,
            databasePathField,
            tableNameField,
            queryField,
            logicalTableIdField,
            FindField(context.Fields, "schema"));
    }

    public string NodeType { get; }

    public NodeConfigEditableFieldInputViewModel SourceModeField { get; }

    public NodeConfigEditableFieldInputViewModel DatabasePathField { get; }

    public NodeConfigEditableFieldInputViewModel TableNameField { get; }

    public NodeConfigEditableFieldInputViewModel QueryField { get; }

    public NodeConfigEditableFieldInputViewModel LogicalTableIdField { get; }

    public NodeConfigEditableFieldInputViewModel? SchemaField { get; }

    public ObservableCollection<SqliteTableOptionViewModel> TableOptions { get; } =
        new();

    [ObservableProperty]
    private string databasePath = string.Empty;

    [ObservableProperty]
    private string sourceMode = TableMode;

    [ObservableProperty]
    private SqliteTableOptionViewModel? selectedTableOption;

    [ObservableProperty]
    private string sqlQuery = string.Empty;

    [ObservableProperty]
    private string logicalTableId = string.Empty;

    [ObservableProperty]
    private bool isLoadingTables;

    [ObservableProperty]
    private string? errorMessage;

    public bool IsTableMode => SourceMode == TableMode;

    public bool IsAllTablesMode => SourceMode == AllTablesMode;

    public bool IsQueryMode => SourceMode == QueryMode;

    public bool IsTableCatalogMode => !IsQueryMode;

    public bool IsSingleResultMode => !IsAllTablesMode;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public string DatabasePathText =>
        _localizationService.GetString("node_config.sqlite.database_path");

    public string BrowseText =>
        _localizationService.GetString("node_config.sqlite.browse");

    public string RefreshText =>
        _localizationService.GetString("node_config.sqlite.refresh_tables");

    public string SourceModeText =>
        _localizationService.GetString("node_config.sqlite.source_mode");

    public string TableModeText =>
        _localizationService.GetString("node_config.sqlite.mode.table");

    public string AllTablesModeText =>
        _localizationService.GetString("node_config.sqlite.mode.all_tables");

    public string QueryModeText =>
        _localizationService.GetString("node_config.sqlite.mode.query");

    public string TableNameText =>
        _localizationService.GetString("node_config.sqlite.table_name");

    public string QueryText =>
        _localizationService.GetString("node_config.sqlite.query");

    public string LogicalTableIdText =>
        _localizationService.GetString("node_config.sqlite.logical_table_id");

    [RelayCommand]
    private void UseTableMode()
    {
        SourceMode = TableMode;
        if (SelectedTableOption?.IsAllTables == true)
        {
            SelectedTableOption = TableOptions.FirstOrDefault(option => !option.IsAllTables);
        }
    }

    [RelayCommand]
    private void UseAllTablesMode()
    {
        SourceMode = AllTablesMode;
        SelectedTableOption = TableOptions.FirstOrDefault(option => option.IsAllTables);
    }

    [RelayCommand]
    private void UseQueryMode()
    {
        SourceMode = QueryMode;
    }

    [RelayCommand]
    private async Task BrowseDatabaseAsync()
    {
        var result = await _fileService.OpenDatabaseAsync(_lifetimeToken);
        if (result.Cancelled || _disposed)
        {
            return;
        }

        if (!result.Opened || string.IsNullOrWhiteSpace(result.Path))
        {
            ErrorMessage = result.ErrorMessage
                ?? _localizationService.GetString(
                    "node_config.sqlite.error.file_picker_failed");
            return;
        }

        DatabasePath = result.Path;
        await RefreshTablesAsync();
    }

    private bool CanRefreshTables()
    {
        return !IsLoadingTables && !string.IsNullOrWhiteSpace(DatabasePath);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshTables))]
    private async Task RefreshTablesAsync()
    {
        var path = DatabasePath.Trim();
        if (path.Length == 0)
        {
            ErrorMessage = _localizationService.GetString(
                "node_config.sqlite.error.database_path_required");
            return;
        }

        CancelRequest();
        var requestCts = CancellationTokenSource.CreateLinkedTokenSource(_lifetimeToken);
        _requestCts = requestCts;
        var cancellationToken = requestCts.Token;
        IsLoadingTables = true;
        ErrorMessage = null;
        try
        {
            var response = await _catalogService.ListTablesAsync(path, cancellationToken);
            if (_disposed || cancellationToken.IsCancellationRequested)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = DescribeError(response.Error);
                return;
            }

            var selectedName = SelectedTableOption?.TableName ?? _originalTableName;
            RebuildTableOptions(
                response.Data.Tables,
                selectedName,
                includeMissingSelection: false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (!_disposed)
            {
                ErrorMessage = ex.Message;
            }
        }
        finally
        {
            if (!_disposed && ReferenceEquals(_requestCts, requestCts))
            {
                IsLoadingTables = false;
                requestCts.Dispose();
                _requestCts = null;
            }
        }
    }

    public bool TryPrepareApply(out string errorMessage)
    {
        var path = DatabasePath.Trim();
        if (path.Length == 0)
        {
            errorMessage = _localizationService.GetString(
                "node_config.sqlite.error.database_path_required");
            return false;
        }

        DatabasePathField.InputValue = path;
        DatabasePathField.HasInputValue = true;
        SourceModeField.InputValue = SourceMode;
        SourceModeField.HasInputValue = true;

        if (IsAllTablesMode)
        {
            ClearField(TableNameField);
            ClearField(QueryField);
            ClearField(LogicalTableIdField);
            if (SchemaField is not null)
            {
                ClearField(SchemaField);
            }
        }
        else if (IsQueryMode)
        {
            var query = SqlQuery.Trim();
            if (query.Length == 0)
            {
                errorMessage = _localizationService.GetString(
                    "node_config.sqlite.error.query_required");
                return false;
            }

            SetField(QueryField, query);
            ClearField(TableNameField);
            SetOptionalField(LogicalTableIdField, LogicalTableId);
            if (SchemaField is not null
                && !string.Equals(query, _originalQuery, StringComparison.Ordinal))
            {
                ClearField(SchemaField);
            }
        }
        else
        {
            var tableName = SelectedTableOption?.TableName?.Trim();
            if (string.IsNullOrWhiteSpace(tableName))
            {
                errorMessage = _localizationService.GetString(
                    "node_config.sqlite.error.table_required");
                return false;
            }

            SetField(TableNameField, tableName);
            ClearField(QueryField);
            SetOptionalField(LogicalTableIdField, LogicalTableId);
            if (SchemaField is not null
                && !string.Equals(tableName, _originalTableName, StringComparison.Ordinal))
            {
                ClearField(SchemaField);
            }
        }

        errorMessage = string.Empty;
        return true;
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(DatabasePathText));
        OnPropertyChanged(nameof(BrowseText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(SourceModeText));
        OnPropertyChanged(nameof(TableModeText));
        OnPropertyChanged(nameof(AllTablesModeText));
        OnPropertyChanged(nameof(QueryModeText));
        OnPropertyChanged(nameof(TableNameText));
        OnPropertyChanged(nameof(QueryText));
        OnPropertyChanged(nameof(LogicalTableIdText));
        RebuildTableOptions(
            TableOptions
                .Where(option => !option.IsAllTables)
                .Select(option => option.TableName!)
                .ToArray(),
            SelectedTableOption?.TableName,
            includeMissingSelection: false);
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        CancelRequest();
    }

    private void RebuildTableOptions(
        IEnumerable<string> tableNames,
        string? selectedTableName,
        bool includeMissingSelection)
    {
        _rebuildingOptions = true;
        try
        {
            TableOptions.Clear();
            var allTables = new SqliteTableOptionViewModel(
                null,
                _localizationService.GetString("node_config.sqlite.all_tables_option"),
                IsAllTables: true);
            TableOptions.Add(allTables);

            foreach (var tableName in tableNames
                .Where(name => !string.IsNullOrWhiteSpace(name))
                .Distinct(StringComparer.Ordinal)
                .OrderBy(name => name, StringComparer.OrdinalIgnoreCase))
            {
                TableOptions.Add(new SqliteTableOptionViewModel(tableName, tableName));
            }

            if (includeMissingSelection
                && !string.IsNullOrWhiteSpace(selectedTableName)
                && TableOptions.All(option => !string.Equals(
                    option.TableName,
                    selectedTableName,
                    StringComparison.Ordinal)))
            {
                TableOptions.Add(
                    new SqliteTableOptionViewModel(selectedTableName, selectedTableName));
            }

            SelectedTableOption = IsAllTablesMode
                ? allTables
                : TableOptions.FirstOrDefault(option => string.Equals(
                    option.TableName,
                    selectedTableName,
                    StringComparison.Ordinal));
        }
        finally
        {
            _rebuildingOptions = false;
        }
    }

    private void CancelRequest()
    {
        _requestCts?.Cancel();
        _requestCts?.Dispose();
        _requestCts = null;
    }

    private string DescribeError(ApiErrorDto? error)
    {
        return error?.Message
            ?? _localizationService.GetString(
                "node_config.sqlite.error.catalog_failed");
    }

    private static string ResolveInitialMode(
        NodeConfigEditableFieldInputViewModel sourceModeField,
        NodeConfigEditableFieldInputViewModel tableNameField,
        NodeConfigEditableFieldInputViewModel queryField)
    {
        if (queryField.HasInputValue
            && !string.IsNullOrWhiteSpace(queryField.InputValue)
            && (!tableNameField.HasInputValue
                || string.IsNullOrWhiteSpace(tableNameField.InputValue)))
        {
            return QueryMode;
        }

        return sourceModeField.InputValue is AllTablesMode or QueryMode
            ? sourceModeField.InputValue
            : TableMode;
    }

    private static NodeConfigEditableFieldInputViewModel? FindField(
        IReadOnlyList<NodeConfigEditableFieldInputViewModel> fields,
        string name)
    {
        return fields.FirstOrDefault(
            field => string.Equals(field.Name, name, StringComparison.Ordinal));
    }

    private static void SetField(
        NodeConfigEditableFieldInputViewModel field,
        string value)
    {
        field.InputValue = value;
        field.HasInputValue = true;
    }

    private static void SetOptionalField(
        NodeConfigEditableFieldInputViewModel field,
        string value)
    {
        var normalized = value.Trim();
        if (normalized.Length == 0)
        {
            ClearField(field);
            return;
        }

        SetField(field, normalized);
    }

    private static void ClearField(NodeConfigEditableFieldInputViewModel field)
    {
        field.HasInputValue = false;
    }

    partial void OnDatabasePathChanged(string value)
    {
        RefreshTablesCommand.NotifyCanExecuteChanged();
    }

    partial void OnSourceModeChanged(string value)
    {
        OnPropertyChanged(nameof(IsTableMode));
        OnPropertyChanged(nameof(IsAllTablesMode));
        OnPropertyChanged(nameof(IsQueryMode));
        OnPropertyChanged(nameof(IsTableCatalogMode));
        OnPropertyChanged(nameof(IsSingleResultMode));
    }

    partial void OnSelectedTableOptionChanged(SqliteTableOptionViewModel? value)
    {
        if (_rebuildingOptions || value is null)
        {
            return;
        }

        SourceMode = value.IsAllTables ? AllTablesMode : TableMode;
    }

    partial void OnIsLoadingTablesChanged(bool value)
    {
        RefreshTablesCommand.NotifyCanExecuteChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }
}
