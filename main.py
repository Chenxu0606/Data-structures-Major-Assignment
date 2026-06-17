import customtkinter as ctk
from tkinter import messagebox
import collections
import time
import heapq

# ==========================================
# 全局视觉美化配置 (Apple 语义化色彩体系)
# ==========================================
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

BG_MAIN = ("#F5F5F7", "#121212")
BG_CARD = ("#FFFFFF", "#1E1E1E")
BG_SIDEBAR = ("#F2F2F7", "#1A1A1F")
COLOR_ACCENT = ("#007AFF", "#0A84FF")
COLOR_SUCCESS = ("#34C759", "#30D158")
COLOR_VIP = ("#FFCC00", "#FFD60A")
BORDER_COLOR = ("#E5E5EA", "#2C2C2E")


class QueueManager:
    """多路分流队列管理器 (小/中/大/VIP)"""

    def __init__(self):
        self.queues = {"S": collections.deque(), "M": collections.deque(), "L": collections.deque(),
                       "VIP": collections.deque()}
        self.counters = {"S": 1, "M": 1, "L": 1, "VIP": 1}
        self.total_served = 0
        self.total_tickets = 0

    def enqueue(self, customer_name, party_size, is_vip=False):
        self.total_tickets += 1
        timestamp = time.time()
        if is_vip:
            queue_type = "VIP"
            ticket_num = f"V{self.counters['VIP']:03d}"
            display_name = "VIP 专属特权"
        else:
            if party_size <= 2:
                queue_type = "S"
                ticket_num = f"S{self.counters['S']:03d}"
                display_name = "舒适小桌 (1-2人)"
            elif 3 <= party_size <= 4:
                queue_type = "M"
                ticket_num = f"M{self.counters['M']:03d}"
                display_name = "精致中桌 (3-4人)"
            else:
                queue_type = "L"
                ticket_num = f"L{self.counters['L']:03d}"
                display_name = "宽敞大桌 (5人以上)"

        self.counters[queue_type] += 1
        self.queues[queue_type].append((ticket_num, customer_name, party_size, timestamp, display_name))
        return ticket_num, display_name

    def get_waiting_status(self):
        return {
            "S_len": len(self.queues["S"]), "M_len": len(self.queues["M"]), "L_len": len(self.queues["L"]),
            "VIP_len": len(self.queues["VIP"]),
            "total_wait": len(self.queues["S"]) + len(self.queues["M"]) + len(self.queues["L"]) + len(
                self.queues["VIP"]),
            "total_served": self.total_served, "total_tickets": self.total_tickets
        }


class TableAssetManager:
    """9 桌物理资产动态演算器 (4小 + 3中 + 2大)"""

    def __init__(self):
        self.total_s_tables = 4;
        self.total_m_tables = 3;
        self.total_l_tables = 2
        self.occupied_s = 0;
        self.occupied_m = 0;
        self.occupied_l = 0

    def allocate(self, party_size):
        if party_size <= 2:
            if self.occupied_s < self.total_s_tables:
                self.occupied_s += 1; return "分配成功：[标准小桌 (1-2人)]", "S"
            elif self.occupied_m < self.total_m_tables:
                self.occupied_m += 1; return "小桌爆满，触发动态资产升级：[指派空闲中桌]", "M"
            elif self.occupied_l < self.total_l_tables:
                self.occupied_l += 1; return "小/中桌皆满，触发极端升级：[指派空闲大桌]", "L"
        elif 3 <= party_size <= 4:
            if self.occupied_m < self.total_m_tables:
                self.occupied_m += 1; return "分配成功：[标准中桌 (3-4人)]", "M"
            elif self.occupied_l < self.total_l_tables:
                self.occupied_l += 1; return "中桌爆满，触发动态资产升级：[指派空闲大桌]", "L"
            elif (self.total_s_tables - self.occupied_s) >= 2:
                self.occupied_s += 2; return "中/大桌爆满，触发【智能拆分算法】：合并 2 张小桌就餐！", "Combined_S"
        else:
            if self.occupied_l < self.total_l_tables:
                self.occupied_l += 1; return "分配成功：[标准大桌 (5人以上)]", "L"
            elif (self.total_m_tables - self.occupied_m) >= 2:
                self.occupied_m += 2; return "大桌爆满，触发【中桌拼桌算法】：成功合并 2 张中桌就餐！", "Combined_M"
            elif (self.total_s_tables - self.occupied_s) >= 3:
                self.occupied_s += 3; return "大/中桌爆满，触发【灾备拼桌算法】：成功合并 3 张小桌就餐！", "Combined_S3"
        return "当前店内无任何可调配的物理空间，请安排至休息区等候。", "None"

    def release_one_table(self, table_type):
        if table_type == "S" and self.occupied_s > 0:
            self.occupied_s -= 1; return True
        elif table_type == "M" and self.occupied_m > 0:
            self.occupied_m -= 1; return True
        elif table_type == "L" and self.occupied_l > 0:
            self.occupied_l -= 1; return True
        return False

    def fill_all(self):
        self.occupied_s = self.total_s_tables; self.occupied_m = self.total_m_tables; self.occupied_l = self.total_l_tables

    def release_all(self):
        self.occupied_s = 0; self.occupied_m = 0; self.occupied_l = 0


# ==========================================
# 【算法再重构核心 5】：支持多量级联扣减的最小堆管理器
# ==========================================
class IngredientHeapManager:
    def __init__(self):
        self.heap = []
        # 预设基础库存
        heapq.heappush(self.heap, (3, "深海三文鱼", 4, "份"))
        heapq.heappush(self.heap, (5, "澳洲和牛肉", 10, "块"))
        heapq.heappush(self.heap, (1, "有机高山生菜", 5, "斤"))

    def add_ingredient(self, name, qty, unit, expiry_days):
        heapq.heappush(self.heap, (expiry_days, name, qty, unit))

    def consume_custom_qty(self, req_qty):
        """【核心重构】级联式控量清库算法：支持管理员自由指定扣除数字"""
        if not self.heap:
            return "EMPTY", []

        # 前置安全拦截：如果堆顶第一批就过期了，必须先启动销毁流程，不允许混合扣减
        if self.heap[0][0] <= 0:
            days, name, qty, unit = heapq.heappop(self.heap)
            return "EXPIRED_DESTROY", [(days, name, qty, unit)]

        consumed_details = []  # 记录本次级联扣除的流水轨迹
        remaining_to_deduct = req_qty

        while remaining_to_deduct > 0 and self.heap:
            # 观察当前的堆顶批次
            days, name, qty, unit = self.heap[0]

            # 再次防护：在级联中如果遇到了过期的批次，就地截断，不再向下扣除
            if days <= 0:
                break

            if qty > remaining_to_deduct:
                # 情况 A：当前批次库存充足，扣完收工
                heapq.heappop(self.heap)
                new_qty = qty - remaining_to_deduct
                heapq.heappush(self.heap, (days, name, new_qty, unit))  # 塞回堆，Down-Heap
                consumed_details.append((name, remaining_to_deduct, unit))
                remaining_to_deduct = 0
            else:
                # 情况 B：当前批次不够扣，直接把这个批次“吃干抹净”出堆，然后顺延到下一批
                heapq.heappop(self.heap)
                consumed_details.append((name, qty, unit))
                remaining_to_deduct -= qty

        if remaining_to_deduct == 0:
            return "SUCCESS", consumed_details
        else:
            # 说明把全库没过期的货全扣光了，还是没能满足管理员输入的巨量需求
            return "PARTIAL_OUT_OF_STOCK", consumed_details

    def simulate_time_pass(self):
        new_list = []
        for days, name, qty, unit in self.heap:
            new_list.append((days - 1, name, qty, unit))
        self.heap = new_list
        heapq.heapify(self.heap)

    def get_sorted_list(self):
        return sorted(self.heap)


class AdvancedRestaurantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("智策 Zhice AI - 智能数据排队叫号系统 V3.6 自由控量版")
        self.geometry("1060x660")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        self.queue_manager = QueueManager()
        self.table_manager = TableAssetManager()
        self.inventory_manager = IngredientHeapManager()

        self.merchant_password = "admin"
        self.grid_columnconfigure(0, weight=3);
        self.grid_columnconfigure(1, weight=6);
        self.grid_rowconfigure(0, weight=1)

        self.create_dashboard_sidebar()
        self.right_container = ctk.CTkFrame(self, fg_color="transparent")
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.right_container.grid_rowconfigure(0, weight=1);
        self.grid_columnconfigure(1, weight=1)

        self.frames = {}
        self.create_customer_frame()
        self.create_merchant_frame()
        self.show_frame("customer")

    def create_dashboard_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=330, corner_radius=20, fg_color=BG_SIDEBAR, border_width=1,
                               border_color=BORDER_COLOR)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20);
        sidebar.pack_propagate(False)

        brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_frame.pack(pady=(25, 15), fill="x", padx=20)
        ctk.CTkLabel(brand_frame, text="⚡ ZHICE AI", font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
                     text_color=COLOR_ACCENT).pack(side="left")
        ctk.CTkLabel(brand_frame, text="自由控量版 V3.6", font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color=("#E5E5EA", "#2C2C2E"), text_color="gray", corner_radius=5, padx=6, pady=2).pack(
            side="left", padx=8)

        self.total_tickets_lbl = self.create_kpi_card(sidebar, "历史总接单/取号量", "0", COLOR_ACCENT)
        self.total_served_lbl = self.create_kpi_card(sidebar, "已就餐接待数", "0", COLOR_SUCCESS)
        self.total_wait_lbl = self.create_kpi_card(sidebar, "当前排队等位桌数", "0", ("#FF3B30", "#FF453A"))

        table_card = ctk.CTkFrame(sidebar, fg_color=BG_CARD, corner_radius=14, border_width=1,
                                  border_color=BORDER_COLOR)
        table_card.pack(pady=(10, 15), fill="x", padx=20)
        ctk.CTkLabel(table_card, text="📊 9座全店实体物理桌位占用", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="gray").pack(anchor="w", padx=15, pady=(8, 2))
        self.table_status_lbl = ctk.CTkLabel(table_card, text="小桌:0/4 | 中桌:0/3 | 大桌:0/2",
                                             font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.table_status_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        detail_card = ctk.CTkFrame(sidebar, fg_color=BG_CARD, corner_radius=14, border_width=1,
                                   border_color=BORDER_COLOR)
        detail_card.pack(pady=(5, 20), fill="both", expand=True, padx=20)
        self.queue_detail_lbl = ctk.CTkLabel(detail_card, text="", justify="left",
                                             font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.queue_detail_lbl.pack(anchor="w", padx=15, pady=15)

    def create_kpi_card(self, parent, label_text, default_val, color_theme):
        card = ctk.CTkFrame(parent, height=75, fg_color=BG_CARD, corner_radius=14, border_width=1,
                            border_color=BORDER_COLOR)
        card.pack(pady=5, fill="x", padx=20);
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=label_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack(
            anchor="w", padx=15, pady=(8, 0))
        val_lbl = ctk.CTkLabel(card, text=default_val, font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
                               text_color=color_theme)
        val_lbl.pack(anchor="w", padx=15, pady=(0, 4))
        return val_lbl

    def create_customer_frame(self):
        frame = ctk.CTkFrame(self.right_container, corner_radius=20, fg_color=BG_CARD, border_width=1,
                             border_color=BORDER_COLOR)
        self.frames["customer"] = frame
        ctk.CTkLabel(frame, text="自助智慧取号系统", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(55, 10))
        ctk.CTkLabel(frame, text="智策动态资产检测，若全店资源充沛将直接免排队放行", font=ctk.CTkFont(size=13),
                     text_color="gray").pack(pady=(0, 30))

        form_container = ctk.CTkFrame(frame, fg_color="transparent").pack(pady=10)
        form_grid = ctk.CTkFrame(frame, fg_color="transparent");
        form_grid.pack()
        ctk.CTkLabel(form_grid, text="顾客尊称", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0,
                                                                                                sticky="w", pady=8)
        self.name_entry = ctk.CTkEntry(form_grid, placeholder_text="例如：陈女士", width=220, height=40, corner_radius=8,
                                       border_color=BORDER_COLOR)
        self.name_entry.grid(row=0, column=1, padx=15, pady=8)
        ctk.CTkLabel(form_grid, text="就餐人数", font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0,
                                                                                                sticky="w", pady=8)
        self.size_entry = ctk.CTkEntry(form_grid, placeholder_text="请输入人数 (纯数字)", width=220, height=40,
                                       corner_radius=8, border_color=BORDER_COLOR)
        self.size_entry.grid(row=1, column=1, padx=15, pady=8)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent");
        btn_frame.pack(pady=35)
        ctk.CTkButton(btn_frame, text="标准智能取号", width=150, height=50, corner_radius=10,
                      font=ctk.CTkFont(size=15, weight="bold"), fg_color=COLOR_ACCENT,
                      command=lambda: self.handle_take_ticket(False)).grid(row=0, column=0, padx=12)
        ctk.CTkButton(btn_frame, text="👑 VIP 特权取号", width=150, height=50, corner_radius=10,
                      font=ctk.CTkFont(size=15, weight="bold"), fg_color=("#E6B800", "#FFD60A"), text_color="black",
                      command=lambda: self.handle_take_ticket(True)).grid(row=0, column=1, padx=12)
        ctk.CTkButton(frame, text="管理后台入口 ⚙️", width=140, height=36, fg_color=BG_MAIN,
                      text_color=("#333333", "#CCCCCC"), corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
                      command=self.verify_and_switch).pack(side="bottom", anchor="e", padx=25, pady=25)

    def create_merchant_frame(self):
        frame = ctk.CTkFrame(self.right_container, corner_radius=20, fg_color=BG_CARD, border_width=1,
                             border_color=BORDER_COLOR)
        self.frames["merchant"] = frame
        ctk.CTkLabel(frame, text="商家中央综合控制台", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20, 5))

        self.tabview = ctk.CTkTabview(frame, fg_color="transparent");
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)
        self.tabview.add("📢 智能叫号与资产演练");
        self.tabview.add("🍎 智策临期食材堆生命周期监控")
        self.setup_calling_tab(self.tabview.tab("📢 智能叫号与资产演练"))
        self.setup_inventory_tab(self.tabview.tab("🍎 智策临期食材堆生命周期监控"))

        ctk.CTkButton(frame, text="← 退出后台", width=110, height=34, fg_color=BG_MAIN,
                      text_color=("#333333", "#CCCCCC"), corner_radius=8,
                      command=lambda: self.show_frame("customer")).pack(side="bottom", anchor="w", padx=25, pady=20)

    def setup_calling_tab(self, tab_frame):
        self.call_board = ctk.CTkLabel(tab_frame, text="系统就绪，等待呼叫",
                                       font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
                                       text_color=COLOR_SUCCESS);
        self.call_board.pack(pady=10)
        ctk.CTkButton(tab_frame, text="📢 调度队列下一位 (处理等位客群)", width=280, height=45, corner_radius=12,
                      font=ctk.CTkFont(size=15, weight="bold"), fg_color=COLOR_SUCCESS,
                      command=self.handle_call_customer).pack(pady=5)

        checkout_frame = ctk.CTkFrame(tab_frame, fg_color="transparent");
        checkout_frame.pack(pady=10)
        ctk.CTkLabel(checkout_frame, text="🍏 模拟单桌顾客就餐完毕（离座释放资产）：",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").grid(row=0, column=0, columnspan=3,
                                                                                       pady=(0, 6))
        ctk.CTkButton(checkout_frame, text="空出 1 张小桌", width=110, height=32, fg_color=COLOR_ACCENT,
                      command=lambda: self.handle_release_single("S")).grid(row=1, column=0, padx=6)
        ctk.CTkButton(checkout_frame, text="空出 1 张中桌", width=110, height=32, fg_color=COLOR_ACCENT,
                      command=lambda: self.handle_release_single("M")).grid(row=1, column=1, padx=6)
        ctk.CTkButton(checkout_frame, text="空出 1 张大桌", width=110, height=32, fg_color=COLOR_ACCENT,
                      command=lambda: self.handle_release_single("L")).grid(row=1, column=2, padx=6)

        sim_btn_frame = ctk.CTkFrame(tab_frame, fg_color="transparent");
        sim_btn_frame.pack(pady=8)
        ctk.CTkButton(sim_btn_frame, text="🔥 一键模拟店内坐满", width=170, height=34, fg_color="#FF9500",
                      text_color="white", command=self.handle_fill_tables).grid(row=0, column=0, padx=10)
        ctk.CTkButton(sim_btn_frame, text="🔄 一键模拟全店离座", width=170, height=34, fg_color="transparent",
                      border_width=1, border_color="#FF3B30", text_color=("#FF3B30", "#FF453A"),
                      command=self.handle_reset_tables).grid(row=0, column=1, padx=10)

    def setup_inventory_tab(self, tab_frame):
        split_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, pady=5)
        split_frame.grid_columnconfigure(0, weight=4);
        split_frame.grid_columnconfigure(1, weight=3)

        left_view = ctk.CTkFrame(split_frame, fg_color=BG_MAIN, corner_radius=10);
        left_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(left_view, text="⚠️ 临期智能堆看板（堆顶决定全局营销策略）",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(pady=5)
        self.heap_list_box = ctk.CTkLabel(left_view, text="", justify="left",
                                          font=ctk.CTkFont(family="Consolas", size=13));
        self.heap_list_box.pack(pady=10, padx=10, fill="both", expand=True)

        inv_ctrl_frame = ctk.CTkFrame(left_view, fg_color="transparent");
        inv_ctrl_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        ctk.CTkButton(inv_ctrl_frame, text="⏳ 模拟时间过去 1 天", fg_color="#FF9500", text_color="white",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self.handle_time_travel).pack(side="left",
                                                                                                      expand=True,
                                                                                                      fill="x", padx=2)

        # 【交互更新】：新增数量输入框 + 精准按钮并排布局
        self.pop_qty_entry = ctk.CTkEntry(inv_ctrl_frame, placeholder_text="数量", width=55, height=32)
        self.pop_qty_entry.insert(0, "1")  # 默认填1
        self.pop_qty_entry.pack(side="left", padx=2)

        ctk.CTkButton(inv_ctrl_frame, text="🥑 控量级联消耗", fg_color="#E6B800", text_color="black",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self.handle_pop_ingredient).pack(side="left",
                                                                                                         expand=True,
                                                                                                         fill="x",
                                                                                                         padx=2)

        right_form = ctk.CTkFrame(split_frame, fg_color="transparent");
        right_form.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(right_form, text="📥 增量食材录入堆算法", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        self.ing_name_entry = ctk.CTkEntry(right_form, placeholder_text="食材名称 (如: 三文鱼)", height=32);
        self.ing_name_entry.pack(fill="x", pady=4)
        self.ing_qty_entry = ctk.CTkEntry(right_form, placeholder_text="数量整数 (如: 15)", height=32);
        self.ing_qty_entry.pack(fill="x", pady=4)
        self.ing_unit_entry = ctk.CTkEntry(right_form, placeholder_text="计量单位 (如: 份)", height=32);
        self.ing_unit_entry.pack(fill="x", pady=4)
        self.ing_expiry_entry = ctk.CTkEntry(right_form, placeholder_text="初始保质期天数 (如: 3)", height=32);
        self.ing_expiry_entry.pack(fill="x", pady=4)
        ctk.CTkButton(right_form, text="执行 O(log N) 堆插入", fg_color=COLOR_ACCENT,
                      command=self.handle_add_ingredient).pack(fill="x", pady=15)

    def show_frame(self, name):
        for f in self.frames.values(): f.grid_forget()
        self.frames[name].grid(row=0, column=0, sticky="nsew");
        self.refresh_dashboard()

    def handle_take_ticket(self, is_vip):
        name = self.name_entry.get().strip();
        size_str = self.size_entry.get().strip()
        if not name or not size_str: messagebox.showwarning("信息不完整", "请确保输入顾客姓名和就餐人数。"); return
        try:
            size = int(size_str)
            if size <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "就餐人数必须为合法的正整数。"); return

        q_type = "VIP" if is_vip else ("S" if size <= 2 else ("M" if size <= 4 else "L"))
        if not len(self.queue_manager.queues[q_type]) > 0:
            alloc_msg, table_type = self.table_manager.allocate(size)
            if table_type != "None":
                self.queue_manager.total_tickets += 1;
                self.queue_manager.total_served += 1
                promo_tip = self.get_ai_marketing_recommendation()
                messagebox.showinfo("绿色通道 - 直接就餐",
                                    f"欢迎您，{name}！系统已为您开启免排队绿色通道。\n\n资产分配反馈：\n{alloc_msg}\n------------------------\n{promo_tip}")
                self.name_entry.delete(0, 'end');
                self.size_entry.delete(0, 'end');
                self.refresh_dashboard();
                return

        num, display_name = self.queue_manager.enqueue(name, size, is_vip)
        self.name_entry.delete(0, 'end');
        self.size_entry.delete(0, 'end')
        messagebox.showinfo("进入排队队列", f"当前对应桌型已满。\n您的号码：{num}\n对应桌型：{display_name}")
        self.refresh_dashboard()

    def get_ai_marketing_recommendation(self):
        if not self.inventory_manager.heap: return "💡 智策AI看板：当前食材库存健康。"
        top_days, top_name, top_qty, top_unit = self.inventory_manager.heap[0]
        if top_days <= 0:
            return f"❌ 智策安全警报：【{top_name}】已过期！系统已阻断供应，请去后台销毁！"
        elif top_days <= 2:
            return f"💡 [智策AI实时推介]\n临期风险资产：【{top_name}】仅剩 {top_days} 天保质期！请协助服务员主推！"
        else:
            return f"🍏 经营状况：全库食材状态优良。"

    def handle_call_customer(self):
        target_q = "VIP" if self.queue_manager.queues["VIP"] else ("S" if self.queue_manager.queues["S"] else (
            "M" if self.queue_manager.queues["M"] else ("L" if self.queue_manager.queues["L"] else None)))
        if target_q:
            customer_data = self.queue_manager.queues[target_q].popleft()
            num, name, size, _, _ = customer_data
            alloc_msg, table_type = self.table_manager.allocate(size)
            if table_type == "None":
                self.queue_manager.queues[target_q].appendleft(customer_data)
                messagebox.showwarning("全店满座", f"呼叫失败！无空间安置 {num} 号 ({name})。请先空出桌位！")
            else:
                self.queue_manager.total_served += 1;
                self.call_board.configure(text=f"请 {num} 号就餐")
                promo_tip = self.get_ai_marketing_recommendation()
                messagebox.showinfo("智策分配成功",
                                    f"【叫号广播】{num} 号 ({name} 顾客) 成功进店\n\n资产分配反馈：\n{alloc_msg}\n------------------------\n{promo_tip}")
        else:
            self.call_board.configure(text="当前无排队");
            messagebox.showwarning("提示", "排队队列为空。")
        self.refresh_dashboard()

    def handle_release_single(self, table_type):
        if self.table_manager.release_one_table(table_type):
            type_map = {"S": "小桌", "M": "中桌", "L": "大桌"}
            msg = f"成功空出 1 张 [{type_map[table_type]}] 桌位！"
            status = self.queue_manager.get_waiting_status()
            if status["total_wait"] > 0: msg += f"\n\n📢 雷达提示：有 {status['total_wait']} 桌客人在等候，请及时调度叫号！"
            messagebox.showinfo("离座成功", msg)
        else:
            messagebox.showwarning("提示", "当前没有正在用餐的该类型桌位。")
        self.refresh_dashboard()

    def handle_time_travel(self):
        self.inventory_manager.simulate_time_pass()
        messagebox.showinfo("时空穿梭", "⏳ 模拟时间过去 1 天！全库食材保质期减 1，已重新整理最小堆。")
        self.refresh_dashboard()

    def handle_add_ingredient(self):
        name = self.ing_name_entry.get().strip();
        qty_str = self.ing_qty_entry.get().strip()
        unit = self.ing_unit_entry.get().strip();
        expiry_str = self.ing_expiry_entry.get().strip()
        if not name or not qty_str or not unit or not expiry_str: messagebox.showwarning("提示", "请填写完整。"); return
        try:
            qty = int(qty_str);
            days = int(expiry_str)
            if qty <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("错误", "数量和保质期必须是正整数！"); return

        self.inventory_manager.add_ingredient(name, qty, unit, days)
        self.ing_name_entry.delete(0, 'end');
        self.ing_qty_entry.delete(0, 'end');
        self.ing_unit_entry.delete(0, 'end');
        self.ing_expiry_entry.delete(0, 'end')
        messagebox.showinfo("成功", f"食材【{name}】成功插入最小堆储备。")
        self.refresh_dashboard()

    def handle_pop_ingredient(self):
        """【处理函数更新】管理员自由控量消耗逻辑"""
        qty_str = self.pop_qty_entry.get().strip()
        try:
            req_qty = int(qty_str)
            if req_qty <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("格式错误", "消耗数量必须是正整数！")
            return

        code, details = self.inventory_manager.consume_custom_qty(req_qty)

        if code == "EMPTY":
            messagebox.showwarning("空仓库", "当前临期食材堆内已无任何数据。")
        elif code == "EXPIRED_DESTROY":
            days, name, qty, unit = details[0]
            messagebox.showerror(
                "🚨 强制安全销毁",
                f"安全阻断！发现堆顶食材【{name}】已过期 {abs(days)} 天！\n\n"
                f"出于食品安全原则，系统已拒绝普通消耗，并强行将该批次共计 {qty} {unit} 执行【整批报废出堆】！"
            )
        elif code == "SUCCESS":
            flow_str = "\n".join([f"• 消耗【{name}】: {q} {u}" for name, q, u in details])
            messagebox.showinfo("扣减成功", f"🎉 管理员成功指定消耗 {req_qty} 个单位！\n\n底层级联消库流水：\n{flow_str}")
        elif code == "PARTIAL_OUT_OF_STOCK":
            flow_str = "\n".join([f"• 消耗【{name}】: {q} {u}" for name, q, u in details])
            total_done = sum([q for _, q, _ in details])
            messagebox.showwarning(
                "全库可用库存耗尽",
                f"警告：管理员索要消耗 {req_qty} 个单位，但目前全库没过期的可用总货量仅剩 {total_done}。\n\n"
                f"现已将可用库存全部清库级联消耗：\n{flow_str}\n\n"
                f"⚠️ 缺口 {req_qty - total_done} 个单位，请采购部火速补货！"
            )
        self.refresh_dashboard()

    def handle_fill_tables(self):
        self.table_manager.fill_all(); self.refresh_dashboard()

    def handle_reset_tables(self):
        self.table_manager.release_all(); self.refresh_dashboard()

    def verify_and_switch(self):
        dialog = ctk.CTkInputDialog(text="安全验证，请输入商家管理密码:", title="安全认证")
        pwd = dialog.get_input()
        if pwd == self.merchant_password:
            self.show_frame("merchant")
        elif pwd is not None:
            messagebox.showerror("验证失败", "管理密码不正确！")

    def refresh_dashboard(self):
        status = self.queue_manager.get_waiting_status()
        self.total_tickets_lbl.configure(text=str(status["total_tickets"]))
        self.total_served_lbl.configure(text=str(status["total_served"]))
        self.total_wait_lbl.configure(text=str(status["total_wait"]))

        self.table_status_lbl.configure(
            text=f"小桌: {self.table_manager.occupied_s}/{self.table_manager.total_s_tables} | "
                 f"中桌: {self.table_manager.occupied_m}/{self.table_manager.total_m_tables} | "
                 f"大桌: {self.table_manager.occupied_l}/{self.table_manager.total_l_tables}"
        )

        detail_text = f"小桌队列 (1-2人):   {status['S_len']:02d} 桌\n中桌队列 (3-4人):   {status['M_len']:02d} 桌\n大桌队列 (5人以上):  {status['L_len']:02d} 桌\n👑 VIP 特权队列:    {status['VIP_len']:02d} 桌"
        self.queue_detail_lbl.configure(text=detail_text)

        heap_snap = self.inventory_manager.get_sorted_list()
        if heap_snap:
            view_lines = []
            for idx, (days, name, qty, unit) in enumerate(heap_snap):
                if days <= 0:
                    status_tag = f"❌ [已过期! 报废销毁] (过期 {abs(days)} 天)"
                elif days == 1:
                    status_tag = "🚨 [极度危急! 主推销库]"
                elif 2 <= days <= 3:
                    status_tag = "⚠️ [临期预警! 建议促销]"
                else:
                    status_tag = "🍏 [安全储备]"
                view_lines.append(f"{status_tag} {name} (剩余: {qty} {unit})")
            self.heap_list_box.configure(text="\n".join(view_lines))
        else:
            self.heap_list_box.configure(text="（当前暂无食材库存）")


if __name__ == "__main__":
    app = AdvancedRestaurantApp()
    app.mainloop()