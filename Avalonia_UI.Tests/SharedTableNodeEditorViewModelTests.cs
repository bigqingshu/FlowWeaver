using System;
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
public sealed class SharedTableNodeEditorViewModelTests
{
    [TestMethod]
    public void FactoryCreatesTypedSharedEditorsAndFallsBackForIncompleteSchema()
    {
        var service = new FakeCatalogService();
        var publish = NodeSpecializedEditorFactory.Create(
            NodeEditorKey.PublishSharedTables,
            PublishContext(
                service,
                exportNames: ["orders"],
                connections: [Connection("c1", "source", "out", "publish", "in")]));
        var read = NodeSpecializedEditorFactory.Create(
            NodeEditorKey.ReadSharedTables,
            ReadContext(service));
        var incompleteRead = NodeSpecializedEditorFactory.Create(
            NodeEditorKey.ReadSharedTables,
            ReadContext(service, includeMembersField: false));

        Assert.IsInstanceOfType<PublishSharedTablesNodeEditorViewModel>(publish);
        Assert.IsInstanceOfType<ReadSharedTablesNodeEditorViewModel>(read);
        Assert.IsNull(incompleteRead);
        Assert.IsNull(NodeSpecializedEditorFactory.Create(
            NodeEditorKey.None,
            ReadContext(service)));
    }

    [TestMethod]
    public void PublishEditorMapsStableInputsAndBuildsUniqueExportNames()
    {
        var service = new FakeCatalogService();
        var editor = PublishSharedTablesNodeEditorViewModel.TryCreate(
            PublishContext(
                service,
                exportNames: ["old_name"],
                connections:
                [
                    Connection("c2", "source_b", "out_b", "publish", "in_b"),
                    Connection("c1", "source_a", "out_a", "publish", "in_a"),
                ]));

        Assert.IsNotNull(editor);
        Assert.HasCount(2, editor.InputMappings);
        Assert.AreEqual("source_b", editor.InputMappings[0].Connection?.SourceNodeId);
        Assert.AreEqual("source_a", editor.InputMappings[1].Connection?.SourceNodeId);
        var configChangedCount = 0;
        editor.ConfigChanged += (_, _) => configChangedCount++;
        editor.InputMappings[0].ExportName = "orders";
        editor.InputMappings[1].ExportName = "customers";

        Assert.AreEqual(2, configChangedCount);

        Assert.IsTrue(editor.TryPrepareApply(out var errorMessage));
        Assert.AreEqual(string.Empty, errorMessage);
        CollectionAssert.AreEqual(
            new[] { "orders", "customers" },
            editor.ExportNamesField.StringArrayItems
                .Select(item => item.Value)
                .ToArray());
    }

    [TestMethod]
    public void ReadEditorReportsSelectedMemberChanges()
    {
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(
                new FakeCatalogService(),
                selectedMembers: ["orders"]));
        Assert.IsNotNull(editor);
        var configChangedCount = 0;
        editor.ConfigChanged += (_, _) => configChangedCount++;

        editor.ClearSelectedMembersCommand.Execute(null);

        Assert.AreEqual(1, configChangedCount);
    }

    [TestMethod]
    public void PublishEditorRejectsMissingDuplicateAndMismatchedExports()
    {
        var service = new FakeCatalogService();
        var editor = PublishSharedTablesNodeEditorViewModel.TryCreate(
            PublishContext(
                service,
                exportNames: ["orders", "orders"],
                connections:
                [
                    Connection("c1", "source_a", "out", "publish", "in_a"),
                    Connection("c2", "source_b", "out", "publish", "in_b"),
                ]));

        Assert.IsNotNull(editor);
        Assert.IsFalse(editor.TryPrepareApply(out var duplicateError));
        StringAssert.Contains(duplicateError, "unique");

        editor.InputMappings[1].ExportName = string.Empty;
        Assert.IsFalse(editor.TryPrepareApply(out var missingError));
        StringAssert.Contains(missingError, "#2");

        var mismatchEditor = PublishSharedTablesNodeEditorViewModel.TryCreate(
            PublishContext(
                service,
                exportNames: ["orders", "customers"],
                connections: [Connection("c1", "source", "out", "publish", "in")]));
        Assert.IsNotNull(mismatchEditor);
        Assert.IsFalse(mismatchEditor.TryPrepareApply(out var mismatchError));
        StringAssert.Contains(mismatchError, "connected input count");
    }

    [TestMethod]
    public async Task ReadEditorLoadsCatalogVersionAndMembersThenBuildsLatestConfig()
    {
        var service = new FakeCatalogService
        {
            SharesResponse = CatalogPage(Share("daily_report", latestVersion: 2)),
            VersionsResponse = VersionPage(
                Version("pub-2", "daily_report", 2, isLatest: true),
                Version("pub-1", "daily_report", 1)),
            MembersResponse = MemberPage(
                Member("pub-2", "customers"),
                Member("pub-2", "orders")),
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(service, shareName: string.Empty, selectedMembers: []));
        Assert.IsNotNull(editor);

        editor.ShareSearchText = "daily";
        await editor.RefreshSharesCommand.ExecuteAsync(null);
        Assert.HasCount(1, editor.ShareOptions);

        editor.SelectedShareOption = editor.ShareOptions[0];
        await WaitUntilAsync(() => editor.MemberOptions.Count == 2);

        Assert.AreEqual("daily_report", editor.ShareName);
        Assert.AreEqual(2, editor.SelectedVersionOption?.PublicationVersion);
        editor.MemberOptions.Single(member => member.ExportName == "orders").IsSelected = true;

        Assert.IsTrue(editor.TryPrepareApply(out var errorMessage));
        Assert.AreEqual(string.Empty, errorMessage);
        Assert.AreEqual("LATEST", editor.VersionPolicyField.InputValue);
        Assert.IsFalse(editor.ExactVersionField?.HasInputValue);
        CollectionAssert.AreEqual(
            new[] { "orders" },
            editor.SelectedMembersField?.StringArrayItems
                .Select(item => item.Value)
                .ToArray());

        editor.ClearSelectedMembersCommand.Execute(null);
        Assert.IsTrue(editor.TryPrepareApply(out _));
        Assert.IsFalse(editor.SelectedMembersField?.HasInputValue);
    }

    [TestMethod]
    public async Task ReadEditorBuildsExactVersionAndBlocksMissingConfiguredMember()
    {
        var service = new FakeCatalogService
        {
            VersionsResponse = VersionPage(
                Version("pub-3", "daily_report", 3, isLatest: true),
                Version("pub-2", "daily_report", 2)),
            MembersResponse = MemberPage(Member("pub-2", "orders")),
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(
                service,
                shareName: "daily_report",
                policy: "EXACT_VERSION",
                exactVersion: "2",
                selectedMembers: ["missing_member"]));
        Assert.IsNotNull(editor);

        await editor.RefreshVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => editor.MemberOptions.Count == 1);

        Assert.AreEqual(2, editor.SelectedVersionOption?.PublicationVersion);
        Assert.IsFalse(editor.TryPrepareApply(out var errorMessage));
        StringAssert.Contains(errorMessage, "no longer exists");

        editor.ClearSelectedMembersCommand.Execute(null);
        editor.MemberOptions[0].IsSelected = true;
        Assert.IsTrue(editor.TryPrepareApply(out _));
        Assert.AreEqual("EXACT_VERSION", editor.VersionPolicyField.InputValue);
        Assert.AreEqual("2", editor.ExactVersionField?.InputValue);
        Assert.IsTrue(editor.ExactVersionField?.HasInputValue);
    }

    [TestMethod]
    public async Task ReadEditorKeepsExistingConfigWhenDirectoryIsOffline()
    {
        var service = new FakeCatalogService
        {
            SharesResponse = ApiResponseEnvelope<SharedPublicationCatalogPageDto>.Failure(
                "ENGINE_OFFLINE",
                "EngineHost is offline."),
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(
                service,
                shareName: "daily_report",
                selectedMembers: ["orders"]));
        Assert.IsNotNull(editor);

        await editor.RefreshSharesCommand.ExecuteAsync(null);

        Assert.IsTrue(editor.HasError);
        Assert.AreEqual("EngineHost is offline.", editor.ErrorMessage);
        Assert.IsTrue(editor.TryPrepareApply(out _));
        Assert.AreEqual("daily_report", editor.ShareNameField.InputValue);
        CollectionAssert.AreEqual(
            new[] { "orders" },
            editor.SelectedMembersField?.StringArrayItems
                .Select(item => item.Value)
                .ToArray());
    }

    [TestMethod]
    public async Task ReadEditorHandlesNullSearchAndShareNameWithoutThrowing()
    {
        var service = new FakeCatalogService
        {
            SearchHandler = (query, _, _, _) =>
            {
                Assert.IsNull(query);
                return Task.FromResult(CatalogPage());
            },
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(service));
        Assert.IsNotNull(editor);

        editor.ShareSearchText = null!;
        await editor.RefreshSharesCommand.ExecuteAsync(null);
        Assert.IsFalse(editor.HasError);

        editor.ShareName = null!;
        Assert.IsFalse(editor.TryPrepareApply(out var errorMessage));
        StringAssert.Contains(errorMessage, "Share name");
        await editor.RefreshVersionsCommand.ExecuteAsync(null);
        Assert.IsTrue(editor.HasError);
    }

    [TestMethod]
    public async Task ReadEditorDiscardsLateShareAndVersionResponsesAndCancelsOldRequests()
    {
        var oldShares = NewCompletion<SharedPublicationCatalogPageDto>();
        var newShares = NewCompletion<SharedPublicationCatalogPageDto>();
        var oldVersions = NewCompletion<SharedPublicationSummaryPageDto>();
        var newVersions = NewCompletion<SharedPublicationSummaryPageDto>();
        CancellationToken oldShareToken = default;
        CancellationToken oldVersionToken = default;
        var service = new FakeCatalogService
        {
            SearchHandler = (query, _, _, token) =>
            {
                if (query == "old")
                {
                    oldShareToken = token;
                    return oldShares.Task;
                }

                return newShares.Task;
            },
            VersionHandler = (shareName, _, _, token) =>
            {
                if (shareName == "old_share")
                {
                    oldVersionToken = token;
                    return oldVersions.Task;
                }

                return newVersions.Task;
            },
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(ReadContext(service));
        Assert.IsNotNull(editor);

        editor.ShareSearchText = "old";
        var oldShareTask = editor.RefreshSharesCommand.ExecuteAsync(null);
        editor.ShareSearchText = "new";
        var newShareTask = editor.RefreshSharesCommand.ExecuteAsync(null);
        newShares.SetResult(CatalogPage(Share("new_share", latestVersion: 1)));
        await newShareTask;
        oldShares.SetResult(CatalogPage(Share("old_share", latestVersion: 1)));
        await oldShareTask;

        Assert.IsTrue(oldShareToken.IsCancellationRequested);
        CollectionAssert.AreEqual(
            new[] { "new_share" },
            editor.ShareOptions.Select(option => option.ShareName).ToArray());

        editor.ShareName = "old_share";
        var oldVersionTask = editor.RefreshVersionsCommand.ExecuteAsync(null);
        editor.ShareName = "new_share";
        var newVersionTask = editor.RefreshVersionsCommand.ExecuteAsync(null);
        newVersions.SetResult(VersionPage(
            Version("new-pub", "new_share", 2, isLatest: true)));
        await newVersionTask;
        oldVersions.SetResult(VersionPage(
            Version("old-pub", "old_share", 1, isLatest: true)));
        await oldVersionTask;

        Assert.IsTrue(oldVersionToken.IsCancellationRequested);
        CollectionAssert.AreEqual(
            new[] { "new-pub" },
            editor.VersionOptions.Select(option => option.PublicationId).ToArray());
    }

    [TestMethod]
    public async Task ReadEditorDiscardsLateMemberResponseWhenVersionChanges()
    {
        var oldMembers = NewCompletion<SharedPublicationMemberPageDto>();
        var newMembers = NewCompletion<SharedPublicationMemberPageDto>();
        CancellationToken oldMemberToken = default;
        var service = new FakeCatalogService
        {
            MemberHandler = (publicationId, _, _, token) =>
            {
                if (publicationId == "old-pub")
                {
                    oldMemberToken = token;
                    return oldMembers.Task;
                }

                return newMembers.Task;
            },
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(ReadContext(service));
        Assert.IsNotNull(editor);

        editor.SelectedVersionOption = new SharedPublicationVersionOptionViewModel(
            Version("old-pub", "daily_report", 1, isLatest: true));
        editor.SelectedVersionOption = new SharedPublicationVersionOptionViewModel(
            Version("new-pub", "daily_report", 2, isLatest: true));
        newMembers.SetResult(MemberPage(Member("new-pub", "new_member")));
        await WaitUntilAsync(() => editor.MemberOptions.Count == 1);
        oldMembers.SetResult(MemberPage(Member("old-pub", "old_member")));
        await Task.Yield();

        Assert.IsTrue(oldMemberToken.IsCancellationRequested);
        CollectionAssert.AreEqual(
            new[] { "new_member" },
            editor.MemberOptions.Select(option => option.ExportName).ToArray());
    }

    [TestMethod]
    public async Task ReadEditorLoadsPagedCatalogWithoutFetchingAllEntries()
    {
        var service = new FakeCatalogService
        {
            SearchHandler = (_, offset, limit, _) => Task.FromResult(
                offset == 0
                    ? CatalogPage(
                        [Share("share-a", 1)],
                        offset: 0,
                        limit: limit,
                        total: 2,
                        hasMore: true)
                    : CatalogPage(
                        [Share("share-b", 1)],
                        offset: offset,
                        limit: limit,
                        total: 2,
                        hasMore: false)),
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(ReadContext(service));
        Assert.IsNotNull(editor);

        await editor.RefreshSharesCommand.ExecuteAsync(null);
        Assert.IsTrue(editor.HasMoreShares);
        await editor.LoadMoreSharesCommand.ExecuteAsync(null);

        CollectionAssert.AreEqual(
            new[] { "share-a", "share-b" },
            editor.ShareOptions.Select(option => option.ShareName).ToArray());
        CollectionAssert.AreEqual(new[] { 0, 1 }, service.ShareOffsets.ToArray());
        Assert.IsFalse(editor.HasMoreShares);
    }

    [TestMethod]
    public async Task ReadEditorPaginatesVersionsAndMembersWithBoundedPageSizes()
    {
        var service = new FakeCatalogService
        {
            VersionHandler = (shareName, offset, limit, _) => Task.FromResult(
                offset == 0
                    ? VersionPage(
                        [Version("pub-2", shareName, 2, isLatest: true)],
                        offset: 0,
                        limit: limit,
                        total: 2,
                        hasMore: true)
                    : VersionPage(
                        [Version("pub-1", shareName, 1)],
                        offset: offset,
                        limit: limit,
                        total: 2,
                        hasMore: false)),
            MemberHandler = (publicationId, offset, limit, _) => Task.FromResult(
                offset == 0
                    ? MemberPage(
                        [Member(publicationId, "orders")],
                        offset: 0,
                        limit: limit,
                        total: 2,
                        hasMore: true)
                    : MemberPage(
                        [Member(publicationId, "customers")],
                        offset: offset,
                        limit: limit,
                        total: 2,
                        hasMore: false)),
        };
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(ReadContext(service));
        Assert.IsNotNull(editor);

        await editor.RefreshVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => editor.MemberOptions.Count == 1);
        await editor.LoadMoreVersionsCommand.ExecuteAsync(null);
        await editor.LoadMoreMembersCommand.ExecuteAsync(null);

        CollectionAssert.AreEqual(
            new[] { 2, 1 },
            editor.VersionOptions.Select(option => option.PublicationVersion).ToArray());
        CollectionAssert.AreEqual(
            new[] { "orders", "customers" },
            editor.MemberOptions.Select(option => option.ExportName).ToArray());
        CollectionAssert.AreEqual(new[] { 0, 1 }, service.VersionOffsets.ToArray());
        CollectionAssert.AreEqual(new[] { 0, 1 }, service.MemberOffsets.ToArray());
        Assert.IsTrue(service.VersionLimits.All(limit => limit == 50));
        Assert.IsTrue(service.MemberLimits.All(limit => limit == 100));
    }

    [TestMethod]
    public void ReadEditorRejectsNonPositiveExactVersion()
    {
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(
                new FakeCatalogService(),
                policy: "EXACT_VERSION",
                exactVersion: "0"));
        Assert.IsNotNull(editor);

        Assert.IsFalse(editor.TryPrepareApply(out var errorMessage));
        StringAssert.Contains(errorMessage, "positive integer");
    }

    [TestMethod]
    public async Task ReadVersionPolicyOptionsUseChineseAndEnglishDisplayText()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var editor = ReadSharedTablesNodeEditorViewModel.TryCreate(
            ReadContext(
                new FakeCatalogService(),
                localizationService: localizationService));
        Assert.IsNotNull(editor);

        Assert.AreEqual("最新版本 (Latest)", editor.LatestText);
        Assert.AreEqual(
            "指定版本 (Exact version)",
            editor.ExactVersionPolicyOptionText);
        Assert.AreEqual("指定版本", editor.ExactVersionTextLabel);
    }

    private static NodeSpecializedEditorContext PublishContext(
        ISharedPublicationCatalogService service,
        string[] exportNames,
        WorkflowDefinitionConnectionListItemViewModel[] connections)
    {
        return Context(
            "PublishSharedTablesNode",
            "publish",
            service,
            [
                Field("share_name", NodeConfigFieldType.String, "daily_report"),
                StringArrayField("export_names", exportNames, required: true),
                Field("retention_seconds", NodeConfigFieldType.Integer, "60"),
            ],
            connections);
    }

    private static NodeSpecializedEditorContext ReadContext(
        ISharedPublicationCatalogService service,
        string shareName = "daily_report",
        string policy = "LATEST",
        string exactVersion = "",
        string[]? selectedMembers = null,
        bool includeMembersField = true,
        ILocalizationService? localizationService = null)
    {
        var fields = new List<NodeConfigEditableFieldInputViewModel>
        {
            Field("share_name", NodeConfigFieldType.String, shareName),
            Field("version_policy", NodeConfigFieldType.Enum, policy),
            Field(
                "exact_version",
                NodeConfigFieldType.Integer,
                exactVersion,
                hasInputValue: exactVersion.Length > 0),
        };
        if (includeMembersField)
        {
            fields.Add(StringArrayField(
                "selected_members",
                selectedMembers ?? ["orders"]));
        }

        return Context(
            "ReadSharedTablesNode",
            "read",
            service,
            fields,
            [],
            localizationService);
    }

    private static NodeSpecializedEditorContext Context(
        string nodeType,
        string nodeInstanceId,
        ISharedPublicationCatalogService service,
        IReadOnlyList<NodeConfigEditableFieldInputViewModel> fields,
        IReadOnlyList<WorkflowDefinitionConnectionListItemViewModel> connections,
        ILocalizationService? localizationService = null)
    {
        return new NodeSpecializedEditorContext
        {
            Node = new WorkflowDefinitionNodeListItemViewModel(
                nodeInstanceId,
                nodeType,
                "1.0",
                nodeType,
                enabled: true,
                configJson: "{}"),
            Fields = fields,
            Connections = connections,
            CatalogService = service,
            LocalizationService = localizationService ?? new JsonLocalizationService(),
            LifetimeToken = CancellationToken.None,
        };
    }

    private static NodeConfigEditableFieldInputViewModel Field(
        string name,
        NodeConfigFieldType type,
        string value,
        bool hasInputValue = true)
    {
        return new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = name,
                Type = type,
                InputValue = value,
                HasInputValue = hasInputValue,
                EnumValues = type == NodeConfigFieldType.Enum
                    ? ["LATEST", "EXACT_VERSION"]
                    : [],
            });
    }

    private static NodeConfigEditableFieldInputViewModel StringArrayField(
        string name,
        string[] values,
        bool required = false)
    {
        return new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = name,
                Type = NodeConfigFieldType.Array,
                ItemType = "string",
                InputValue = "[]",
                HasInputValue = values.Length > 0,
                Required = required,
                StringArrayValues = values,
            });
    }

    private static WorkflowDefinitionConnectionListItemViewModel Connection(
        string connectionId,
        string sourceNodeId,
        string sourcePort,
        string targetNodeId,
        string targetPort)
    {
        return new WorkflowDefinitionConnectionListItemViewModel(
            connectionId,
            sourceNodeId,
            sourcePort,
            targetNodeId,
            targetPort);
    }

    private static SharedPublicationCatalogEntryDto Share(
        string shareName,
        int latestVersion)
    {
        return new SharedPublicationCatalogEntryDto
        {
            ShareName = shareName,
            LatestPublishedVersion = latestVersion,
            PublishedVersionCount = latestVersion,
            LatestMemberCount = 2,
            LatestCreatedAt = DateTimeOffset.Parse("2026-07-11T00:00:00Z"),
        };
    }

    private static SharedPublicationSummaryDto Version(
        string publicationId,
        string shareName,
        int version,
        bool isLatest = false,
        string status = "PUBLISHED")
    {
        return new SharedPublicationSummaryDto
        {
            PublicationId = publicationId,
            ShareName = shareName,
            PublicationVersion = version,
            ProducerWorkflowId = "wf-1",
            ProducerRunId = "run-1",
            Status = status,
            MemberCount = 2,
            IsLatestPublished = isLatest,
            CreatedAt = DateTimeOffset.Parse("2026-07-11T00:00:00Z"),
        };
    }

    private static SharedPublicationMemberDto Member(
        string publicationId,
        string exportName)
    {
        return new SharedPublicationMemberDto
        {
            PublicationId = publicationId,
            ExportName = exportName,
            TableRefId = $"table-{exportName}",
            ExactTableVersion = 1,
        };
    }

    private static ApiResponseEnvelope<SharedPublicationCatalogPageDto> CatalogPage(
        params SharedPublicationCatalogEntryDto[] entries)
    {
        return CatalogPage(
            entries,
            offset: 0,
            limit: 50,
            total: entries.Length,
            hasMore: false);
    }

    private static ApiResponseEnvelope<SharedPublicationCatalogPageDto> CatalogPage(
        SharedPublicationCatalogEntryDto[] entries,
        int offset,
        int limit,
        int total,
        bool hasMore)
    {
        return ApiResponseEnvelope<SharedPublicationCatalogPageDto>.Success(
            new SharedPublicationCatalogPageDto
            {
                Items = entries,
                Offset = offset,
                Limit = limit,
                Total = total,
                HasMore = hasMore,
            });
    }

    private static ApiResponseEnvelope<SharedPublicationSummaryPageDto> VersionPage(
        params SharedPublicationSummaryDto[] versions)
    {
        return VersionPage(
            versions,
            offset: 0,
            limit: 50,
            total: versions.Length,
            hasMore: false);
    }

    private static ApiResponseEnvelope<SharedPublicationSummaryPageDto> VersionPage(
        SharedPublicationSummaryDto[] versions,
        int offset,
        int limit,
        int total,
        bool hasMore)
    {
        return ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
            new SharedPublicationSummaryPageDto
            {
                Items = versions,
                Offset = offset,
                Limit = limit,
                Total = total,
                HasMore = hasMore,
            });
    }

    private static ApiResponseEnvelope<SharedPublicationMemberPageDto> MemberPage(
        params SharedPublicationMemberDto[] members)
    {
        return MemberPage(
            members,
            offset: 0,
            limit: 100,
            total: members.Length,
            hasMore: false);
    }

    private static ApiResponseEnvelope<SharedPublicationMemberPageDto> MemberPage(
        SharedPublicationMemberDto[] members,
        int offset,
        int limit,
        int total,
        bool hasMore)
    {
        return ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
            new SharedPublicationMemberPageDto
            {
                Items = members,
                Offset = offset,
                Limit = limit,
                Total = total,
                HasMore = hasMore,
            });
    }

    private static TaskCompletionSource<ApiResponseEnvelope<T>> NewCompletion<T>()
    {
        return new TaskCompletionSource<ApiResponseEnvelope<T>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
    }

    private static async Task WaitUntilAsync(Func<bool> condition)
    {
        for (var attempt = 0; attempt < 100; attempt++)
        {
            if (condition())
            {
                return;
            }

            await Task.Delay(10);
        }

        Assert.Fail("Timed out waiting for asynchronous editor state.");
    }

    private sealed class FakeCatalogService : ISharedPublicationCatalogService
    {
        public ApiResponseEnvelope<SharedPublicationCatalogPageDto> SharesResponse { get; init; } =
            CatalogPage();

        public ApiResponseEnvelope<SharedPublicationSummaryPageDto> VersionsResponse { get; init; } =
            VersionPage();

        public ApiResponseEnvelope<SharedPublicationMemberPageDto> MembersResponse { get; init; } =
            MemberPage();

        public Func<
            string?,
            int,
            int,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>>>? SearchHandler
        { get; init; }

        public Func<
            string,
            int,
            int,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>>>? VersionHandler
        { get; init; }

        public Func<
            string,
            int,
            int,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>>>? MemberHandler
        { get; init; }

        public List<int> ShareOffsets { get; } = [];

        public List<int> VersionOffsets { get; } = [];

        public List<int> VersionLimits { get; } = [];

        public List<int> MemberOffsets { get; } = [];

        public List<int> MemberLimits { get; } = [];

        public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> SearchSharesAsync(
            string? query,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            ShareOffsets.Add(offset);
            return SearchHandler?.Invoke(query, offset, limit, cancellationToken)
                ?? Task.FromResult(SharesResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListVersionsAsync(
            string shareName,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            VersionOffsets.Add(offset);
            VersionLimits.Add(limit);
            return VersionHandler?.Invoke(shareName, offset, limit, cancellationToken)
                ?? Task.FromResult(VersionsResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListMembersAsync(
            string publicationId,
            int offset,
            int limit,
            CancellationToken cancellationToken = default)
        {
            MemberOffsets.Add(offset);
            MemberLimits.Add(limit);
            return MemberHandler?.Invoke(publicationId, offset, limit, cancellationToken)
                ?? Task.FromResult(MembersResponse);
        }
    }
}
