using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class SqlMappingTableNodeEditorViewModelTests
{
    [TestMethod]
    public async Task BrowseDatabaseLoadsTablesAndAppliesSelectedTable()
    {
        var catalog = new FakeSqliteTableCatalogService("orders", "customers");
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(@"C:\data\sales.db"),
                catalog));
        Assert.IsNotNull(editor);

        await editor.BrowseDatabaseCommand.ExecuteAsync(null);

        Assert.AreEqual(@"C:\data\sales.db", editor.DatabasePath);
        Assert.AreEqual(@"C:\data\sales.db", catalog.LastDatabasePath);
        CollectionAssert.AreEqual(
            new[] { null, "customers", "orders" },
            editor.TableOptions.Select(option => option.TableName).ToArray());

        editor.SelectedTableOption = editor.TableOptions.Single(
            option => option.TableName == "orders");
        editor.LogicalTableId = "daily_orders";
        Assert.IsTrue(editor.TryPrepareApply(out var errorMessage), errorMessage);

        Assert.AreEqual("table", editor.SourceModeField.InputValue);
        Assert.AreEqual("orders", editor.TableNameField.InputValue);
        Assert.AreEqual("daily_orders", editor.LogicalTableIdField.InputValue);
        Assert.IsFalse(editor.QueryField.HasInputValue);
    }

    [TestMethod]
    public void AllTablesModeClearsSingleResultFields()
    {
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(null),
                new FakeSqliteTableCatalogService(),
                databasePath: @"C:\data\sales.db",
                tableName: "orders",
                logicalTableId: "daily_orders",
                schemaPresent: true));
        Assert.IsNotNull(editor);

        editor.UseAllTablesModeCommand.Execute(null);
        Assert.IsTrue(editor.TryPrepareApply(out var errorMessage), errorMessage);

        Assert.AreEqual("all_tables", editor.SourceModeField.InputValue);
        Assert.IsFalse(editor.TableNameField.HasInputValue);
        Assert.IsFalse(editor.QueryField.HasInputValue);
        Assert.IsFalse(editor.LogicalTableIdField.HasInputValue);
        Assert.IsFalse(editor.SchemaField?.HasInputValue);
    }

    [TestMethod]
    public void LegacyQueryConfigIsDetectedAndPreserved()
    {
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(null),
                new FakeSqliteTableCatalogService(),
                databasePath: @"C:\data\sales.db",
                query: "SELECT id FROM orders",
                logicalTableId: "order_ids",
                sourceModePresent: false));
        Assert.IsNotNull(editor);

        Assert.IsTrue(editor.IsQueryMode);
        Assert.IsTrue(editor.TryPrepareApply(out var errorMessage), errorMessage);

        Assert.AreEqual("query", editor.SourceModeField.InputValue);
        Assert.AreEqual("SELECT id FROM orders", editor.QueryField.InputValue);
        Assert.AreEqual("order_ids", editor.LogicalTableIdField.InputValue);
        Assert.IsFalse(editor.TableNameField.HasInputValue);
    }

    [TestMethod]
    public void TableModeRequiresSelection()
    {
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(null),
                new FakeSqliteTableCatalogService(),
                databasePath: @"C:\data\sales.db"));
        Assert.IsNotNull(editor);

        Assert.IsFalse(editor.TryPrepareApply(out var errorMessage));
        StringAssert.Contains(errorMessage, "Select a table");
    }

    [TestMethod]
    public void EditorReportsConfigPropertyChanges()
    {
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(null),
                new FakeSqliteTableCatalogService(),
                databasePath: @"C:\data\sales.db",
                tableName: "orders"));
        Assert.IsNotNull(editor);
        var configChangedCount = 0;
        editor.ConfigChanged += (_, _) => configChangedCount++;

        editor.LogicalTableId = "daily_orders";

        Assert.AreEqual(1, configChangedCount);
    }

    [TestMethod]
    public async Task RefreshDropsTableMissingFromNewDatabase()
    {
        var editor = SqlMappingTableNodeEditorViewModel.TryCreate(
            Context(
                new FakeSqliteDatabaseFileService(null),
                new FakeSqliteTableCatalogService("customers"),
                databasePath: @"C:\data\new.db",
                tableName: "orders"));
        Assert.IsNotNull(editor);

        await editor.RefreshTablesCommand.ExecuteAsync(null);

        Assert.IsNull(editor.SelectedTableOption);
        CollectionAssert.AreEqual(
            new[] { null, "customers" },
            editor.TableOptions.Select(option => option.TableName).ToArray());
        Assert.IsFalse(editor.TryPrepareApply(out _));
    }

    private static NodeSpecializedEditorContext Context(
        ISqliteDatabaseFileService fileService,
        ISqliteTableCatalogService catalogService,
        string databasePath = "",
        string tableName = "",
        string query = "",
        string logicalTableId = "",
        bool sourceModePresent = true,
        bool schemaPresent = false)
    {
        return new NodeSpecializedEditorContext
        {
            Node = new WorkflowDefinitionNodeListItemViewModel(
                "sql",
                "SqlMappingNode",
                "1.0",
                "SQLite",
                enabled: true,
                configJson: "{}"),
            Fields =
            [
                Field(
                    "source_mode",
                    NodeConfigFieldType.Enum,
                    "table",
                    sourceModePresent,
                    ["table", "all_tables", "query"]),
                Field("database_path", NodeConfigFieldType.String, databasePath),
                Field("table_name", NodeConfigFieldType.String, tableName),
                Field("query", NodeConfigFieldType.String, query),
                Field("logical_table_id", NodeConfigFieldType.String, logicalTableId),
                Field("schema", NodeConfigFieldType.Array, "[]", schemaPresent),
            ],
            Connections = [],
            CatalogService = new UnusedSharedPublicationCatalogService(),
            SqliteTableCatalogService = catalogService,
            SqliteDatabaseFileService = fileService,
            LocalizationService = new JsonLocalizationService(),
            LifetimeToken = CancellationToken.None,
        };
    }

    private static NodeConfigEditableFieldInputViewModel Field(
        string name,
        NodeConfigFieldType type,
        string value,
        bool? hasInputValue = null,
        IReadOnlyList<string>? enumValues = null)
    {
        return new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = name,
                Type = type,
                InputValue = value,
                HasInputValue = hasInputValue ?? value.Length > 0,
                EnumValues = enumValues ?? [],
                ItemType = type == NodeConfigFieldType.Array ? "object" : null,
            });
    }

    private sealed class FakeSqliteDatabaseFileService : ISqliteDatabaseFileService
    {
        private readonly string? _path;

        public FakeSqliteDatabaseFileService(string? path)
        {
            _path = path;
        }

        public Task<SqliteDatabaseFileOpenResult> OpenDatabaseAsync(
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                _path is null
                    ? SqliteDatabaseFileOpenResult.Cancel()
                    : SqliteDatabaseFileOpenResult.Success(_path));
        }
    }

    private sealed class FakeSqliteTableCatalogService : ISqliteTableCatalogService
    {
        private readonly string[] _tables;

        public FakeSqliteTableCatalogService(params string[] tables)
        {
            _tables = tables;
        }

        public string? LastDatabasePath { get; private set; }

        public Task<ApiResponseEnvelope<SqliteTableCatalogDto>> ListTablesAsync(
            string databasePath,
            CancellationToken cancellationToken = default)
        {
            LastDatabasePath = databasePath;
            return Task.FromResult(
                ApiResponseEnvelope<SqliteTableCatalogDto>.Success(
                    new SqliteTableCatalogDto { Tables = _tables }));
        }
    }

    private sealed class UnusedSharedPublicationCatalogService :
        ISharedPublicationCatalogService
    {
        public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> SearchSharesAsync(
            string? query,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            throw new System.NotSupportedException();
        }

        public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListVersionsAsync(
            string shareName,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            throw new System.NotSupportedException();
        }

        public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListMembersAsync(
            string publicationId,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            throw new System.NotSupportedException();
        }
    }
}
